"""Crédit Agricole CIB's public Talentsoft board and full vacancy pages."""

import asyncio
import html
import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from pydantic import Field

from trading_radar.config import Company
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, ExperienceEvidence, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://jobs.ca-cib.com"
SEARCH = ORIGIN + "/pages/offre/listeoffre.aspx"
PAGE_SIZE = 100


def job_url(value: str) -> tuple[str, str]:
    url = urljoin(ORIGIN, value)
    parts = urlsplit(url)
    match = re.fullmatch(r"/offre-de-emploi/emploi-[a-z0-9_-]+_(\d+)\.aspx", parts.path)
    if (
        parts.scheme != "https"
        or parts.netloc != "jobs.ca-cib.com"
        or parts.query
        or parts.fragment
        or not match
    ):
        raise SourceUnavailable("invalid CA CIB job URL")
    return url, match[1]


def parse_page(text: str, page: int, limit: int) -> tuple[int, list[dict]]:
    nodes = list(Document(text).root.walk())
    counts = with_class(nodes, "ts-ol-pagination__title")
    totals = {re.fullmatch(r"Nombre de résultats\s*:\s*(\d+) offre\(s\)", clean(n)) for n in counts}
    if not totals or None in totals:
        raise SourceUnavailable("CA CIB result count missing")
    values = {int(m[1]) for m in totals if m}
    if len(values) != 1 or max(values) > limit:
        raise SourceUnavailable("CA CIB inconsistent or excessive result count")
    total = values.pop()
    current = {clean(n) for n in with_class(nodes, "ts-ol-pagination-list-item__link--active")}
    if current != {str(page)}:
        raise SourceUnavailable("CA CIB wrong page")
    rows = []
    for node in with_class(nodes, "ts-offer-card__title-link"):
        url, identifier = job_url(node.attrs.get("href", ""))
        reference = node.attrs.get("title", "")
        if not re.fullmatch(r"20\d{2}-" + re.escape(identifier), reference) or not clean(node):
            raise SourceUnavailable("CA CIB card reference/title missing")
        rows.append({"id": identifier, "reference": reference, "title": clean(node), "url": url})
    expected = min(PAGE_SIZE, max(0, total - (page - 1) * PAGE_SIZE))
    if len(rows) != expected or len({r["id"] for r in rows}) != len(rows):
        raise SourceUnavailable("CA CIB short or duplicate page")
    return total, rows


def ca_experience_evidence(value: str) -> list[ExperienceEvidence]:
    """Read only the employer's dedicated experience-level field.

    Preserve its exact value as evidence. Unknown wording, reversed ranges and
    values outside the model's bounds supply neither a proof nor a minimum.
    The caller must pass fldapplicantcriteria_experiencelevel, never body text.
    """
    match = re.fullmatch(
        r"(?P<low>[0-9]{1,2})\s*(?:-\s*(?P<high>[0-9]{1,2})\s*(?:ans|years)|"
        r"ans et plus|years and more)",
        value,
    )
    if not match:
        return []
    low = int(match["low"])
    if match["high"] is not None and low > int(match["high"]):
        return []
    return [
        ExperienceEvidence(
            minimum_years=low,
            kind="professional",
            origin="employer_field",
            method="ca_cib_experience_level",
            excerpt=value,
        )
    ]


def parse_detail(text: str, row: dict, config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    refs = with_class(nodes, "ts-offer-page__reference")
    if len(refs) != 1 or " ".join(refs[0].text(without_headings=True).split()) != row["reference"]:
        raise SourceUnavailable("CA CIB detail reference mismatch")
    titles = with_class(nodes, "ts-offer-page__title")
    fields: dict[str, str] = {}
    for node in nodes:
        key = node.attrs.get("id", "")
        if key.startswith(("fldjobdescription_", "fldapplicantcriteria_", "fldlocation_")):
            if key in fields:
                raise SourceUnavailable("CA CIB duplicate detail field")
            fields[key] = clean(node)
    required = [
        "fldjobdescription_jobtitle",
        "fldjobdescription_description1",
        "fldjobdescription_contract",
        "fldlocation_joblocation",
        "fldlocation_location_geographicalareacollection",
    ]
    if any(not fields.get(k) for k in required) or not any(
        v for k, v in fields.items() if k.startswith("fldapplicantcriteria_")
    ):
        raise SourceUnavailable("CA CIB description, criteria or location missing")
    title = fields["fldjobdescription_jobtitle"]
    if len(titles) != 1 or clean(titles[0]) != title or title != row["title"]:
        raise SourceUnavailable("CA CIB detail title mismatch")
    start = fields.get("fldjobdescription_date1") or None
    if start:
        try:
            start = datetime.strptime(start, "%d/%m/%Y").date().isoformat()
        except ValueError:
            raise SourceUnavailable("invalid CA CIB employment start date") from None
    evidence = ca_experience_evidence(fields.get("fldapplicantcriteria_experiencelevel", ""))
    # All employer criteria are preserved, including requirements omitted from the summary.
    description = "\n".join(
        "<p>" + html.escape(value) + "</p>"
        for key, value in fields.items()
        if value and key.startswith(("fldjobdescription_", "fldapplicantcriteria_"))
    )
    return RawJob(
        company=config.name,
        title=title,
        source=source,
        source_type="official",
        external_id=row["reference"],
        apply_url=row["url"],
        source_url=row["url"],
        description=description,
        location=fields["fldlocation_joblocation"]
        + ", "
        + fields["fldlocation_location_geographicalareacollection"],
        expected_start_date=start,
        employment_type=fields["fldjobdescription_contract"],
        minimum_experience_years=evidence[0].minimum_years if evidence else None,
        experience_evidence=evidence,
        # The visible date is explicitly labelled Update date, not publication.
        raw_payload={"fields": fields},
    )


class CACIBOptions(SearchOptions):
    search_terms: list[str] = Field(default_factory=list, max_length=0)


class CACIBCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH:
            raise ValueError("Use the verified CA CIB public board URL")
        self.source, self.config, self.http = source, config, http
        self.options = CACIBOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("CA CIB scan time budget exceeded") from None

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        rows, seen = [], set()
        page, total = 1, None
        while True:
            text = await self.http.get_text(
                f"{SEARCH}?page={page}&LCID=1036", self.config.request_interval, self.source
            )
            count, batch = parse_page(text, page, self.options.max_results_per_query)
            if total is not None and count != total:
                raise SourceUnavailable("CA CIB total changed during pagination")
            total = count
            for row in batch:
                if row["id"] in seen:
                    raise SourceUnavailable("CA CIB repeated vacancy between pages")
                seen.add(row["id"])
                title = normalize_text(row["title"])
                if (
                    not self.options.title_terms
                    or any(has(title, t) for t in self.options.title_terms)
                ) and not any(has(title, t) for t in self.options.exclude_title_terms):
                    rows.append(row)
            if len(seen) == total:
                break
            page += 1
        if len(rows) > self.options.max_details:
            raise SourceUnavailable("CA CIB detail limit exceeded")
        jobs = []
        for row in rows:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
