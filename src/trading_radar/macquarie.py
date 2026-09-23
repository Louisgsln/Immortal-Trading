"""Public Macquarie Avature search and detailed job pages."""

import asyncio
import html
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from trading_radar.config import Company
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.macquarie_experience import macquarie_sales_trading_evidence
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://recruitment.macquarie.com"
SEARCH = ORIGIN + "/en_US/careers/SearchJobs/"
DETAIL = ORIGIN + "/en_US/careers/JobDetail"
PAGE_SIZE = 9


def job_url(value: str) -> tuple[str, str]:
    parts = urlsplit(value)
    query = parse_qs(parts.query, keep_blank_values=True)
    identifier = query.get("jobId", [""])[0]
    if (
        parts.scheme != "https"
        or parts.netloc != "recruitment.macquarie.com"
        or parts.path != "/en_US/careers/JobDetail"
        or parts.fragment
        or query != {"jobId": [identifier]}
        or not identifier.isascii()
        or not identifier.isdigit()
    ):
        raise SourceUnavailable("invalid Macquarie job URL")
    return DETAIL + "?jobId=" + identifier, identifier


def parse_page(text: str, term: str, offset: int, limit: int) -> tuple[int, list[dict]]:
    nodes = list(Document(text).root.walk())
    inputs = [
        n.attrs.get("value") for n in nodes if n.tag == "input" and n.attrs.get("name") == "search"
    ]
    if inputs != [term]:
        raise SourceUnavailable("Macquarie search filter not preserved")
    counts = [
        re.fullmatch(r"(\d+) items?", clean(n))
        for n in nodes
        if n.tag == "h2" and "section__header--top" in n.attrs.get("class", "").split()
    ]
    if len(counts) != 1 or not counts[0]:
        raise SourceUnavailable("Macquarie result count missing")
    total = int(counts[0][1])
    if total > limit:
        raise SourceUnavailable("Macquarie result limit exceeded")
    current = with_class(nodes, "currentPageLink")
    if total and (len(current) != 1 or clean(current[0]) != f"Page {offset // PAGE_SIZE + 1}"):
        raise SourceUnavailable("Macquarie wrong page")
    rows = []
    for article in with_class(nodes, "article--result"):
        titles = [n for n in article.walk() if n.tag == "h3"]
        links = [n for n in titles[0].walk() if n.tag == "a"] if len(titles) == 1 else []
        if len(links) != 1 or not clean(links[0]):
            raise SourceUnavailable("Macquarie card title missing")
        url, identifier = job_url(links[0].attrs.get("href", ""))
        rows.append({"id": identifier, "title": clean(links[0]), "url": url})
    if len(rows) != min(PAGE_SIZE, max(0, total - offset)) or len({r["id"] for r in rows}) != len(
        rows
    ):
        raise SourceUnavailable("Macquarie short or duplicate page")
    return total, rows


def parse_detail(text: str, row: dict, config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    titles = [n for n in with_class(nodes, "title--11") if n.tag == "h2"]
    roots = with_class(nodes, "article__content__fields")
    body = with_class(nodes, "section--without--border--top")
    if len(titles) != 1 or clean(titles[0]) != row["title"] or len(roots) != 1 or len(body) != 1:
        raise SourceUnavailable("Macquarie title mismatch or detail missing")
    fields = with_class([*roots[0].walk(), *body[0].walk()], "article__content__view__field")
    metadata = {}
    descriptions, locations, contracts = [], [], []
    for field in fields:
        labels = with_class(field.walk(), "article__content__view__field__label")
        values = with_class(field.walk(), "article__content__view__field__value")
        if len(values) != 1 or len(labels) > 1:
            raise SourceUnavailable("Macquarie detail field ambiguous")
        value = clean(values[0])
        if labels:
            label = clean(labels[0])
            if label in metadata:
                raise SourceUnavailable("Macquarie duplicate metadata")
            metadata[label] = value
        classes = field.attrs.get("class", "").split()
        if "field--location" in classes:
            locations.append(value)
        elif "field--employmentterm" in classes:
            contracts.append(value)
        elif not any(c.startswith("field--") for c in classes):
            descriptions.append(value)
    headings = {clean(n) for n in body[0].walk() if n.tag == "h3"}
    # Both the actual role and the candidate requirements must be present, beyond boilerplate.
    requirements = ""
    requirement_paragraphs = ""
    for label in ("What role will you play?", "What you offer"):
        sections = [
            n
            for n in body[0].walk()
            if n.tag == "article" and any(x.tag == "h3" and clean(x) == label for x in n.walk())
        ]
        if (
            label not in headings
            or len(sections) != 1
            or not any(
                clean(n)
                for n in with_class(sections[0].walk(), "article__content__view__field__value")
            )
        ):
            raise SourceUnavailable("Macquarie responsibilities or requirements missing")
        if label == "What you offer":
            requirement_values = [
                clean(n)
                for n in with_class(sections[0].walk(), "article__content__view__field__value")
            ]
            requirements = " ".join(requirement_values)
            requirement_paragraphs = "\n".join(
                "<p>" + html.escape(value) + "</p>" for value in requirement_values
            )
    if (
        metadata.get("Job ID") != row["id"]
        or not descriptions
        or not all(descriptions)
        or not locations
        or not all(locations)
        or len(contracts) != 1
        or not contracts[0]
    ):
        raise SourceUnavailable("Macquarie identity, description, location or contract missing")
    levels = {normalize_text(part) for part in contracts[0].split(",")[1:]}
    ranges = re.findall(
        r"\b(\d+)\s*[-–]\s*(\d+)\s+years[’']?\s+(?:of\s+)?(?:[A-Za-z]+\s+){0,3}experience\b",
        requirements,
        re.I,
    )
    if any(int(low) > int(high) for low, high in ranges):
        raise SourceUnavailable("Macquarie contradictory experience range")
    evidence = macquarie_sales_trading_evidence(requirement_paragraphs)
    minima = [int(low) for low, _ in ranges] + [item.minimum_years for item in evidence]
    return RawJob(
        company=config.name,
        title=row["title"],
        source=source,
        source_type="official",
        external_id=row["id"],
        apply_url=row["url"],
        source_url=row["url"],
        description="\n".join("<p>" + html.escape(value) + "</p>" for value in descriptions),
        location="; ".join(dict.fromkeys(locations)),
        employment_type=contracts[0],
        minimum_experience_years=max(minima, default=None),
        experience_evidence=evidence,
        seniority_hint="junior"
        if "junior" in levels
        else "senior"
        if levels and levels <= {"senior", "mid senior"}
        else None,
        # A generic Date label is not assumed to be an original publication date.
        raw_payload={"metadata": metadata},
    )


class MacquarieCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH:
            raise ValueError("Use the verified Macquarie public search URL")
        self.source, self.config, self.http = source, config, http
        self.options = SearchOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Macquarie scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        targets: dict[str, dict] = {}
        for term in self.options.search_terms:
            offset, expected = 0, None
            seen = set()
            while expected is None or offset < expected:
                query = urlencode(
                    {"search": term, "jobRecordsPerPage": PAGE_SIZE, "jobOffset": offset}
                )
                text = await self.http.get_text(
                    SEARCH + "?" + query, self.config.request_interval, self.source
                )
                total, rows = parse_page(text, term, offset, self.options.max_results_per_query)
                if expected is not None and total != expected:
                    raise SourceUnavailable("Macquarie total changed during pagination")
                expected = total
                for row in rows:
                    if row["id"] in seen:
                        raise SourceUnavailable("Macquarie repeated vacancy between pages")
                    seen.add(row["id"])
                    title = normalize_text(row["title"])
                    if (
                        not self.options.title_terms
                        or any(has(title, t) for t in self.options.title_terms)
                    ) and not any(has(title, t) for t in self.options.exclude_title_terms):
                        if row["id"] in targets and targets[row["id"]] != row:
                            raise SourceUnavailable("Macquarie conflicting vacancy across searches")
                        targets[row["id"]] = row
                offset += len(rows)
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Macquarie detail limit exceeded")
        jobs = []
        for row in targets.values():
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
