"""Capula's explicitly published Workable Markdown catalogue and full role details."""

import asyncio
import html
import re
from datetime import date

from pydantic import Field

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import normalize_text
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit, rejection_reason

BOARD = "https://apply.workable.com/capula-investment-management-ltd/"


class WorkableOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def listing(text: str, total: int) -> list[dict[str, str]]:
    if (
        not text.startswith("# Capula — All Open Positions\n")
        or "| Title | Department | Location | Type | Salary | Posted | Details |" not in text
        or not 0 <= total <= 1999
    ):
        raise SourceUnavailable("Workable catalogue header or total changed")
    rows = []
    seen = set()
    for line in text.splitlines():
        if not line.startswith("| ") or line.startswith("| Title |"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 7 or any(not part for part in parts):
            raise SourceUnavailable("Workable catalogue row incomplete")
        link = re.fullmatch(
            r"\[View\]\(" + re.escape(BOARD) + r"jobs/view/([A-F0-9]{10})\.md\)", parts[6]
        )
        if not link or link[1] in seen:
            raise SourceUnavailable("Workable catalogue identity mismatch or duplicate")
        try:
            date.fromisoformat(parts[5])
        except ValueError:
            raise SourceUnavailable("Workable posted calendar date invalid") from None
        seen.add(link[1])
        rows.append(
            dict(
                zip(
                    ("title", "department", "location", "contract", "salary", "posted"),
                    parts[:6],
                    strict=True,
                )
            )
            | {"id": link[1], "detail": BOARD + "jobs/view/" + link[1] + ".md"}
        )
    if len(rows) != total:
        raise SourceUnavailable("Workable incomplete catalogue")
    return rows


def markdown_html(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = raw.strip().replace("**", "")
        if not line:
            continue
        heading = re.fullmatch(r"(#{1,4}) (.+)", line)
        bullet = re.fullmatch(r"-\s+(.+)", line)
        if heading:
            level = len(heading[1])
            lines.append(f"<h{level}>" + html.escape(heading[2]) + f"</h{level}>")
        elif bullet:
            lines.append("<ul><li>" + html.escape(bullet[1]) + "</li></ul>")
        else:
            lines.append("<p>" + html.escape(line) + "</p>")
    return "\n".join(lines)


def detail(text: str, row: dict[str, str], source: str, company: Company) -> RawJob | None:
    heading = "# " + row["title"] + "\n"
    banner = (
        "> Capula · " + row["location"] + " · " + row["contract"] + " · Posted " + row["posted"]
    )
    apply = BOARD + "j/" + row["id"] + "/apply"
    if (
        not text.startswith(heading)
        or text.splitlines().count(banner) != 1
        or text.splitlines().count("**Department:** " + row["department"]) != 1
        or any(
            text.splitlines().count(section) != 1
            for section in ("## Description", "## Requirements", "## Apply")
        )
        or re.findall(r"\[Apply at Capula\]\(([^)]+)\)", text) != [apply]
    ):
        raise SourceUnavailable("Workable detail identity, requirements or apply link changed")
    description = text.split("## Description\n", 1)[1].split("## Apply\n", 1)[0].strip()
    if not description or not description.split("## Requirements", 1)[0].strip():
        raise SourceUnavailable("Workable full description missing")
    if "whilst we are not actively recruiting" in normalize_text(description):
        return None
    return RawJob(
        company=company.name,
        source=source,
        source_type="official",
        external_id=row["id"],
        title=row["title"],
        location=row["location"],
        employment_type=None if row["contract"] == "—" else row["contract"],
        description=markdown_html(description),
        apply_url=apply,
        source_url=row["detail"],
        raw_payload={"posted_calendar_date": row["posted"], "department": row["department"]},
    )


class WorkablePublicCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if (
            config.name != "Capula"
            or config.tenant != "capula-investment-management-ltd"
            or config.career_url != BOARD
        ):
            raise ValueError("Use the verified public Capula Workable catalogue")
        self.source, self.config, self.http = source, config, http
        self.options = WorkableOptions(**config.options)

    async def text(self, url: str) -> str:
        return await self.http.get_text(url, self.config.request_interval, self.source)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Workable scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        guide = await self.text(BOARD + "llms.txt")
        counts = re.findall(
            r"All open roles \(GET `" + re.escape(BOARD) + r"jobs\.md`\): (\d+) current openings",
            guide,
        )
        if not guide.startswith("# Capula Careers\n") or len(counts) != 1:
            raise SourceUnavailable("Workable public catalogue declaration missing")
        total = int(counts[0])
        if total > self.options.max_results_per_query:
            raise SourceUnavailable("Workable catalogue exceeds result limit")
        first = await self.text(BOARD + "jobs.md")
        rows = listing(first, total)
        audit = SelectionAudit("public_catalogue")
        selected = []
        for row in rows:
            reason = rejection_reason(row["title"], self.options)
            audit.record(reason, row["title"], row["id"])
            if reason is None:
                selected.append(row)
        if len(selected) > self.options.max_details:
            raise SourceUnavailable("Workable detail limit exceeded")
        jobs = []
        for row in selected:
            job = detail(await self.text(row["detail"]), row, self.source, self.config)
            if job is not None:
                jobs.append(job)
        if (
            await self.text(BOARD + "jobs.md") != first
            or await self.text(BOARD + "llms.txt") != guide
        ):
            raise SourceUnavailable("Workable catalogue changed during collection")
        return Collection(
            jobs=jobs,
            complete=False,
            scope_complete=True,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
