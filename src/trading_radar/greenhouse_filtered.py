"""Verified public Greenhouse boards, filtered without inferring closures."""

import asyncio
import re
from datetime import UTC, date, datetime
from typing import Literal
from urllib.parse import parse_qsl, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.drw_campus import drw_campus_junior
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text, plain_text
from trading_radar.search_scope import SearchOptions

API = "https://boards-api.greenhouse.io/v1/boards/"
BOARDS = {
    "imc": ("IMC", "job-boards.eu.greenhouse.io"),
    "drweng": ("DRW", "job-boards.greenhouse.io"),
    "flowtraders": ("Flow Traders", "job-boards.greenhouse.io"),
    "jumptrading": ("Jump Trading", "www.jumptrading.com"),
    "xtxmarketstechnologies": ("XTX Markets", "job-boards.greenhouse.io"),
}


class GreenhouseOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def imc_start(content: str) -> str | None:
    months = "January|February|March|April|May|June|July|August|September|October|November|December"
    matches = re.findall(
        rf"\b(?:start dates in|full-time(?: employment)?(?: starting)? in)\s+"
        rf"((?:{months})(?: (?:and|or) (?:{months}))? 20\d{{2}})\b",
        plain_text(content),
        re.IGNORECASE,
    )
    # Preserve the published alternatives instead of selecting one date for the candidate.
    return " / ".join(dict.fromkeys(matches)) or None


def instant(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SourceUnavailable("invalid Greenhouse timestamp")
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SourceUnavailable("invalid Greenhouse timestamp") from None
    if date.tzinfo is None:
        raise SourceUnavailable("Greenhouse timestamp lacks timezone")
    return date.astimezone(UTC)


def metadata(row: dict) -> dict:
    items = row.get("metadata")
    if not isinstance(items, list):
        raise SourceUnavailable("Greenhouse metadata missing")
    fields = {}
    for item in items:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or "value" not in item
        ):
            raise SourceUnavailable("invalid Greenhouse metadata field")
        if item["name"] in fields:
            raise SourceUnavailable("duplicate Greenhouse metadata field")
        fields[item["name"]] = item["value"]
    return fields


def xtx_trading_technology(row: dict) -> bool:
    departments = row.get("departments")
    if not isinstance(departments, list) or any(
        not isinstance(d, dict) or not isinstance(d.get("name"), str) or not d["name"].strip()
        for d in departments
    ):
        raise SourceUnavailable("XTX department metadata missing or invalid")
    if "Tradingdev ETD Tech" not in {d["name"] for d in departments}:
        return False
    title = normalize_text(row["title"])
    if not any(has(title, term) for term in ["software", "developer", "engineer"]):
        return False
    if not isinstance(row.get("content"), str):
        raise SourceUnavailable("XTX role description missing")
    text = plain_text(row["content"])
    # Require evidence in the candidate's role, excluding the generic firm introduction.
    sections = re.split(r"\bThe Role\b", text, flags=re.IGNORECASE)
    if len(sections) != 2:
        raise SourceUnavailable("XTX role section missing or ambiguous")
    role = re.split(r"\bEssential Attributes\b", sections[1], flags=re.IGNORECASE)[0]
    # This department also contains ML infrastructure roles: department alone is insufficient.
    return has(normalize_text(role), "exchange trading development team")


def jump_trading_technology(row: dict) -> bool:
    """Recognize two verified developer role patterns, never the firm's introduction.

    Department alone is insufficient: Core Development also builds general business
    tools. Keep this extension narrow until other role formats are audited.
    """
    title = normalize_text(row["title"])
    if not any(has(title, term) for term in ["software engineer", "quantitative developer"]):
        return False
    departments = row.get("departments")
    if not isinstance(departments, list) or not any(
        isinstance(department, dict)
        and isinstance(department.get("name"), str)
        and department["name"].strip() in {"Core Development", "Front Office"}
        for department in departments
    ):
        return False
    if not isinstance(row.get("content"), str):
        return False
    text = normalize_text(plain_text(row["content"]).replace("’", "'"))
    sections = text.split("what you ll do")
    if len(sections) != 2:
        return False
    duties_and_requirements = sections[1].split("skills you ll need")
    if len(duties_and_requirements) != 2:
        return False
    duties = duties_and_requirements[0]
    if has(title, "software engineer"):
        return all(
            has(duties, evidence)
            for evidence in [
                "collaborate with traders",
                "design technical solutions",
                "software applications",
            ]
        )
    # Quant developer introductions describe this particular position, followed by
    # full-cycle development duties; production support alone is insufficient.
    position = sections[0].split("as a quantitative developer")
    return (
        len(position) == 2
        and all(
            has(position[1], evidence)
            for evidence in [
                "build and improve the platforms that drive the trading team",
                "quantitative researchers",
                "trading infrastructure",
            ]
        )
        and all(
            has(duties, evidence)
            for evidence in ["full cycle development", "writing testing", "debugging code"]
        )
    )


def jump_track_record_minimum(content: str) -> int | None:
    """The audited coding track record in Jump's required skills is a minimum.

    Do not generalize corporate track records or optional skills into experience.
    This intentionally covers only the verified coding requirement phrase.
    """
    text = plain_text(content)
    sections = re.split(r"\bSkills\s+You.{0,3}ll\s+Need\b", text, flags=re.IGNORECASE)
    if len(sections) != 2:
        return None
    required = re.split(
        r"\b(?:Nice to Have|Preferred Qualifications|Benefits|About Us)\b",
        sections[1],
        flags=re.IGNORECASE,
    )[0]
    minima = []
    for clause in re.split(r"[.!?;]", required):
        if re.search(
            r"\b(?:preferred|preferably|desirable|advantageous|nice to have|a plus|optional)\b",
            clause,
            re.IGNORECASE,
        ):
            continue
        match = re.search(
            r"^\s*:?\s*(\d{1,2})\s*\+\s*years?\s+track record of solving "
            r"challenging problems through coding\b",
            clause,
            re.IGNORECASE,
        )
        if match:
            minima.append(int(match[1]))
    return max(minima) if minima else None


def parse_board(
    payload: object, source: str, config: Company, options: GreenhouseOptions
) -> list[RawJob]:
    if not isinstance(payload, dict) or not isinstance(payload.get("meta"), dict):
        raise SourceUnavailable("Greenhouse board metadata missing")
    rows, total = payload.get("jobs"), payload["meta"].get("total")
    if (
        type(total) is not int
        or not 0 <= total <= options.max_results_per_query
        or not isinstance(rows, list)
        or len(rows) != total
    ):
        raise SourceUnavailable("Greenhouse incomplete or excessive board")
    expected_company, host = BOARDS[config.tenant]
    seen = set()
    jobs = []
    for row in rows:
        if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] <= 0:
            raise SourceUnavailable("invalid Greenhouse posting identifier")
        identifier = str(row["id"])
        if identifier in seen:
            raise SourceUnavailable("duplicate Greenhouse posting identifier")
        seen.add(identifier)
        if any(
            not isinstance(row.get(k), str) or not row[k].strip()
            for k in ["title", "company_name", "absolute_url"]
        ):
            raise SourceUnavailable("incomplete Greenhouse posting")
        if row["company_name"].strip() != expected_company:
            raise SourceUnavailable("Greenhouse employer mismatch")
        url = row["absolute_url"]
        parts = urlsplit(url)
        path = f"/{config.tenant}/jobs/{identifier}"
        valid_query = not parts.query
        if config.tenant == "jumptrading":
            path = "/hr/job"
            valid_query = parse_qsl(parts.query, keep_blank_values=True) == [("gh_jid", identifier)]
        if (
            (parts.scheme, parts.netloc, parts.path) != ("https", host, path)
            or not valid_query
            or parts.fragment
        ):
            raise SourceUnavailable("Greenhouse posting URL identity mismatch")
        if "internal_job_id" not in row or (
            row["internal_job_id"] is not None
            and (type(row["internal_job_id"]) is not int or row["internal_job_id"] <= 0)
        ):
            raise SourceUnavailable("Greenhouse job identity missing")
        # Greenhouse documents null internal_job_id as a prospect post, not an open role.
        if row["internal_job_id"] is None:
            continue
        is_xtx = config.tenant == "xtxmarketstechnologies"
        # XTX explicitly returns metadata: null; absence is not an accepted schema change.
        fields = {} if is_xtx and "metadata" in row and row["metadata"] is None else metadata(row)
        trading_technology = (
            xtx_trading_technology(row)
            if is_xtx
            else jump_trading_technology(row)
            if config.tenant == "jumptrading"
            else False
        )
        if config.tenant == "flowtraders":
            if not isinstance(fields.get("Division"), str) or not fields["Division"].strip():
                raise SourceUnavailable("Flow Traders division missing")
            if fields["Division"] == "Events":
                continue
        if config.tenant == "imc":
            if "Is Hidden Job?" not in fields or (
                fields["Is Hidden Job?"] is not None and type(fields["Is Hidden Job?"]) is not bool
            ):
                raise SourceUnavailable("IMC visibility metadata changed")
            if fields["Is Hidden Job?"] is True:
                continue
        title = normalize_text(row["title"])
        if (
            not trading_technology
            and options.title_terms
            and not any(has(title, t) for t in options.title_terms)
        ) or any(has(title, t) for t in options.exclude_title_terms):
            continue
        if not isinstance(row.get("content"), str) or not plain_text(row["content"]):
            raise SourceUnavailable("Greenhouse full description missing")
        location = row.get("location")
        if (
            not isinstance(location, dict)
            or not isinstance(location.get("name"), str)
            or not location["name"].strip()
        ):
            raise SourceUnavailable("Greenhouse posting location missing")
        contract, start = None, None
        junior: Literal["junior", "senior"] | None = None
        if config.tenant == "imc":
            if "Worker Sub Type" not in fields or fields["Worker Sub Type"] not in {
                "Graduate",
                "Experienced",
                "Intern",
                "Working Student",
                "Temporary",
            }:
                raise SourceUnavailable("IMC worker level missing or unknown")
            contract = fields["Worker Sub Type"]
            junior = "junior" if contract == "Graduate" else None
            if junior:
                start = imc_start(row["content"])
        elif config.tenant == "drweng":
            contract = fields.get("Employment Type")
            start = fields.get("Target Start Date")
            if (
                not isinstance(contract, str)
                or not contract.strip()
                or not isinstance(start, str)
                or not start.strip()
            ):
                raise SourceUnavailable("DRW contract or target start missing")
            # A target season is useful evidence, but never invent an exact start day.
            start = start.strip()
            junior = "junior" if drw_campus_junior(row["title"], row["content"], fields) else None
        elif config.tenant == "flowtraders":
            if "Start Date" not in fields:
                raise SourceUnavailable("Flow Traders start metadata missing")
            value = fields["Start Date"]
            if value not in (None, ""):
                if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise SourceUnavailable("invalid Flow Traders start date")
                try:
                    start = date.fromisoformat(value).isoformat()
                except ValueError:
                    raise SourceUnavailable("invalid Flow Traders start date") from None
        elif config.tenant == "jumptrading":
            contract = fields.get("Employment Type")
            if contract not in (
                "Full-time - Experienced",
                "Full-time - Campus",
                "Jump Trading - Intern",
            ):
                raise SourceUnavailable("Jump Trading employment type missing or changed")
            junior = "junior" if contract == "Full-time - Campus" else None
        jobs.append(
            RawJob(
                company=config.name,
                source=source,
                source_type="official",
                external_id=identifier,
                title=row["title"].strip(),
                apply_url=url,
                source_url=url,
                location=location["name"].strip(),
                description=row["content"],
                employment_type=contract,
                seniority_hint=junior,
                minimum_experience_years=(
                    jump_track_record_minimum(row["content"])
                    if config.tenant == "jumptrading"
                    else None
                ),
                role_hint="trading_technology" if trading_technology else None,
                expected_start_date=start,
                date_posted=instant(row.get("first_published")),
                application_deadline=instant(row.get("application_deadline")),
                # updated_at is not a publication date. Keep only relevant metadata as evidence.
                raw_payload={
                    "internal_job_id": row["internal_job_id"],
                    **({"departments": [d["name"] for d in row["departments"]]} if is_xtx else {}),
                    "fields": {
                        k: fields[k]
                        for k in fields
                        if k
                        in {
                            "Employment Type",
                            "Target Start Date",
                            "Worker Sub Type",
                            "Website Job Category Filter",
                            "Start Date",
                            "Division",
                        }
                    },
                },
            )
        )
    if len(jobs) > options.max_details:
        raise SourceUnavailable("Greenhouse selected-job limit exceeded")
    return jobs


class GreenhouseFilteredCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.tenant not in BOARDS or config.name != BOARDS[config.tenant][0]:
            raise ValueError("Use a verified Greenhouse board and employer")
        self.source, self.config, self.http = source, config, http
        self.options = GreenhouseOptions(**config.options)

    async def collect(self) -> Collection:
        before = self.http.counts[self.source]
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                payload = await self.http.get_json(
                    API + self.config.tenant + "/jobs?content=true",
                    self.config.request_interval,
                    self.source,
                )
                jobs = parse_board(payload, self.source, self.config, self.options)
        except TimeoutError:
            raise SourceUnavailable("Greenhouse scan time budget exceeded") from None
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
