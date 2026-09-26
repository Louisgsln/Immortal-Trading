"""Audited public Lever board, bounded pagination and verified posting identities."""

import asyncio
import html
from uuid import UUID

from pydantic import Field

from trading_radar.config import Company
from trading_radar.description_sections import visible_text
from trading_radar.html_page import Document, Element
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text, plain_text
from trading_radar.search_scope import SearchOptions

API = "https://api.lever.co/v0/postings/"
BOARDS = {"belvederetrading": "Belvedere Trading"}
PAGE_SIZE = 100


class LeverOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


def posting_id(row: object) -> str:
    if not isinstance(row, dict) or not isinstance(row.get("id"), str):
        raise SourceUnavailable("Lever posting identifier missing")
    identifier = row["id"]
    try:
        valid = str(UUID(identifier)) == identifier
    except ValueError:
        valid = False
    if not valid:
        raise SourceUnavailable("invalid Lever posting identifier")
    return identifier


def section_content(content: str) -> str:
    """Flatten list wrappers only if every visible word is preserved, in order."""
    root = Document(content).root
    items: list[str] = []

    def visit(node: Element) -> None:
        if node.tag in {"script", "style", "template", "noscript"} or "hidden" in node.attrs:
            return
        if node.tag == "li":
            items.append(" ".join(visible_text(node).split()))
            return
        for child in node.children:
            if isinstance(child, Element):
                visit(child)

    visit(root)
    if items and all(items) and " ".join(items) == " ".join(visible_text(root).split()):
        return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"
    return content


def parse_board(
    payload: object, source: str, config: Company, options: LeverOptions
) -> list[RawJob]:
    if not isinstance(payload, list) or len(payload) > options.max_results_per_query:
        raise SourceUnavailable("Lever incomplete or excessive board")
    seen = set()
    jobs = []
    for row in payload:
        identifier = posting_id(row)
        if identifier in seen:
            raise SourceUnavailable("duplicate Lever posting identifier")
        seen.add(identifier)
        url = f"https://jobs.lever.co/{config.tenant}/{identifier}"
        if row.get("hostedUrl") != url or row.get("applyUrl") != url + "/apply":
            raise SourceUnavailable("Lever posting URL identity mismatch")
        if not isinstance(row.get("text"), str) or not row["text"].strip():
            raise SourceUnavailable("Lever posting title missing")
        fields = row.get("categories")
        if not isinstance(fields, dict) or any(
            not isinstance(fields.get(k), str) or not fields[k].strip()
            for k in ("department", "location", "team", "commitment")
        ):
            raise SourceUnavailable("Lever job categories missing or changed")
        if fields["commitment"] not in {"Full-Time", "Intern"}:
            raise SourceUnavailable("Lever employment type missing or changed")
        title = normalize_text(row["text"])
        if (
            fields["department"] != "Trading"
            or (options.title_terms and not any(has(title, term) for term in options.title_terms))
            or any(has(title, term) for term in options.exclude_title_terms)
        ):
            continue
        if not isinstance(row.get("description"), str) or not plain_text(row["description"]):
            raise SourceUnavailable("Lever full description missing")
        lists = row.get("lists")
        if not isinstance(lists, list) or any(
            not isinstance(item, dict)
            or any(
                not isinstance(item.get(k), str) or not plain_text(item[k])
                for k in ("text", "content")
            )
            for item in lists
        ):
            raise SourceUnavailable("Lever description sections missing or changed")
        additional = row.get("additional", "")
        if not isinstance(additional, str):
            raise SourceUnavailable("Lever additional description changed")
        description = (
            row["description"]
            + "".join(
                f"<section><h3>{html.escape(item['text'])}</h3>"
                + section_content(item["content"])
                + "</section>"
                for item in lists
            )
            + additional
        )
        jobs.append(
            RawJob(
                company=config.name,
                source=source,
                source_type="official",
                external_id=identifier,
                title=row["text"].strip(),
                source_url=url,
                apply_url=url + "/apply",
                description=description,
                location=fields["location"].strip(),
                employment_type=fields["commitment"],
                seniority_hint="junior"
                if fields["team"] == "Campus - Quantitative Trading"
                and fields["commitment"] == "Full-Time"
                else None,
                # Lever createdAt is not documented as a publication date.
                raw_payload={
                    "categories": {
                        k: fields[k] for k in ("department", "location", "team", "commitment")
                    }
                },
            )
        )
    if len(jobs) > options.max_details:
        raise SourceUnavailable("Lever selected-job limit exceeded")
    return jobs


class LeverFilteredCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.tenant not in BOARDS or config.name != BOARDS[config.tenant]:
            raise ValueError("Use a verified Lever board and employer")
        self.source, self.config, self.http = source, config, http
        self.options = LeverOptions(**config.options)

    async def collect(self) -> Collection:
        before = self.http.counts[self.source]

        async def page(offset: int) -> list:
            result = await self.http.get_json(
                f"{API}{self.config.tenant}?mode=json&skip={offset}&limit={PAGE_SIZE}",
                self.config.request_interval,
                self.source,
            )
            if not isinstance(result, list) or len(result) > PAGE_SIZE:
                raise SourceUnavailable("Lever pagination format changed")
            return result

        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                rows: list = []
                seen: set[str] = set()
                first = None
                while True:
                    current = await page(len(rows))
                    if first is None:
                        first = current
                    ids = [posting_id(row) for row in current]
                    if len(set(ids)) != len(ids) or seen.intersection(ids):
                        raise SourceUnavailable("Lever pagination repeats posting identifiers")
                    rows.extend(current)
                    seen.update(ids)
                    if len(rows) > self.options.max_results_per_query:
                        raise SourceUnavailable("Lever board result limit exceeded")
                    if len(current) < PAGE_SIZE:
                        break
                if len(first) == PAGE_SIZE and await page(0) != first:
                    raise SourceUnavailable("Lever pagination changed during scan")
                jobs = parse_board(rows, self.source, self.config, self.options)
        except TimeoutError:
            raise SourceUnavailable("Lever scan time budget exceeded") from None
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
