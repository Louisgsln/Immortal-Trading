"""Bounded searches on the employer's public Avature catalogue."""

import asyncio
import html
import re
from datetime import date, datetime
from urllib.parse import urlencode, urlsplit

from trading_radar.config import Company
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, ExperienceEvidence, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.optiver_sections import description_html
from trading_radar.search_scope import SearchOptions

ORIGIN = "https://jobs.totalenergies.com"
SEARCH = ORIGIN + "/en_US/careers/SearchJobs"
_PATH = re.compile(r"/en_US/careers/JobDetail/[A-Za-z0-9%-]+/(\d+)")


def job_id(url: str) -> str:
    parts = urlsplit(url)
    match = _PATH.fullmatch(parts.path)
    if (
        not match
        or (parts.scheme, parts.netloc) != ("https", "jobs.totalenergies.com")
        or parts.query
        or parts.fragment
    ):
        raise SourceUnavailable("invalid TotalEnergies vacancy URL")
    return match[1]


def parse_page(text: str, term: str, offset: int, limit: int) -> tuple[int, list[dict[str, str]]]:
    nodes = list(Document(text).root.walk())
    if [
        n.attrs.get("value") for n in nodes if n.tag == "input" and n.attrs.get("name") == "search"
    ] != [term]:
        raise SourceUnavailable("TotalEnergies search identity mismatch")
    legends = {clean(n) for n in with_class(nodes, "list-controls__text__legend")}
    match = (
        re.fullmatch(r"(\d+)-(\d+) of (\d+) results", next(iter(legends)))
        if len(legends) == 1
        else None
    )
    short = re.fullmatch(r"(\d+) results?", next(iter(legends))) if len(legends) == 1 else None
    if short and offset == 0 and int(short[1]) <= 20:
        total = int(short[1])
    elif match and int(match[1]) == offset + 1 and int(match[2]) == min(offset + 20, int(match[3])):
        total = int(match[3])
    else:
        raise SourceUnavailable("TotalEnergies pagination range missing or inconsistent")
    if total > limit or offset > total:
        raise SourceUnavailable("TotalEnergies result limit exceeded")
    cards = with_class(nodes, "article--result")
    if len(cards) != min(20, total - offset):
        raise SourceUnavailable("TotalEnergies result count mismatch")
    rows = []
    for card in cards:
        children = list(card.walk())
        titles = [n for n in children if n.tag == "h3"]
        links = [n for n in titles[0].walk() if n.tag == "a"] if len(titles) == 1 else []
        if len(links) != 1 or not clean(links[0]):
            raise SourceUnavailable("TotalEnergies vacancy title missing")
        url = links[0].attrs.get("href", "")
        row = dict(id=job_id(url), url=url, title=clean(links[0]))
        for key, cls in {
            "country": "jobCountry",
            "employment": "employmentType",
            "published": "jobCreationDate",
            "employer": "jobEmployerCompany",
        }.items():
            values = [clean(n) for n in with_class(children, "list-item-" + cls)]
            if len(values) != 1 or not values[0]:
                raise SourceUnavailable("TotalEnergies vacancy metadata missing")
            row[key] = values[0]
        try:
            row["published"] = datetime.strptime(row["published"], "%d-%m-%Y").date().isoformat()
        except ValueError:
            raise SourceUnavailable("invalid TotalEnergies publication day") from None
        apply = [n.attrs.get("href") for n in children if n.tag == "a" and clean(n) == "Apply"]
        external_apply = bool(
            len(apply) == 1
            and isinstance(apply[0], str)
            and re.fullmatch(
                r"https://fa-eocc-saasfaprod1\.fa\.ocs\.oraclecloud\.com/hcmUI/CandidateExperience/en/sites/CX/jobs/preview/\d+/apply/email",
                apply[0],
            )
        )
        if (
            apply != [ORIGIN + "/en_US/careers/ApplicationMethods?jobId=" + row["id"]]
            and not external_apply
        ):
            raise SourceUnavailable("TotalEnergies application identifier mismatch")
        rows.append(row)
    if len({r["id"] for r in rows}) != len(rows):
        raise SourceUnavailable("duplicate TotalEnergies vacancy")
    return total, rows


def parse_detail(text: str, row: dict[str, str], config: Company, source: str) -> RawJob:
    nodes = list(Document(text).root.walk())
    if [n.attrs.get("href") for n in nodes if n.attrs.get("rel") == "canonical"] != [
        row["url"]
    ] or [clean(n) for n in with_class(nodes, "banner__text__title")] != [row["title"]]:
        raise SourceUnavailable("TotalEnergies detail identity mismatch")
    links = [n.attrs.get("href") for n in nodes if n.tag == "a" and clean(n) == "Apply"]
    apply = ORIGIN + "/en_US/careers/ApplicationMethods?jobId=" + row["id"]
    if links != [apply]:
        raise SourceUnavailable("TotalEnergies detail application mismatch")
    fields: dict[str, str] = {}
    for field in with_class(nodes, "article__content__view__field"):
        children = list(field.walk())
        labels = [clean(n) for n in children if n.tag == "dt"]
        if not labels:
            continue
        values = [clean(n) for n in children if n.tag == "dd"]
        if len(labels) != 1 or len(values) != 1 or labels[0] in fields:
            raise SourceUnavailable("ambiguous TotalEnergies detail fields")
        fields[labels[0]] = values[0]
    for label, key in {
        "Country": "country",
        "Employer company": "employer",
        "Type of contract": "employment",
    }.items():
        if fields.get(label) != row[key]:
            raise SourceUnavailable("TotalEnergies card/detail metadata mismatch")
    sections = {}
    for article in with_class(nodes, "article--details"):
        children = list(article.walk())
        headers = [
            clean(n) for n in with_class(children, "article__header__text__title") if n.tag == "h3"
        ]
        if not headers:
            continue  # Unlabelled corporate boilerplate is outside the description.
        bodies = with_class(children, "article__content__view")
        if len(headers) != 1 or len(bodies) != 1 or headers[0] in sections:
            raise SourceUnavailable("ambiguous TotalEnergies description sections")
        sections[headers[0]] = description_html(bodies[0])
    if not {"Activities", "Candidate Profile"}.issubset(sections) or any(
        len(clean(Document(sections[k]).root)) < 30 for k in ["Activities", "Candidate Profile"]
    ):
        raise SourceUnavailable("TotalEnergies full description missing")
    description = "".join(f"<h3>{html.escape(k)}</h3>{v}" for k, v in sections.items())
    evidence = []
    minimum = None
    experience = fields.get("Experience", "")
    if match := re.fullmatch(r"Minimum (\d{1,2}) years?", experience):
        minimum = int(match[1])
        evidence.append(
            ExperienceEvidence(
                minimum_years=minimum,
                kind="professional",
                origin="employer_field",
                method="totalenergies_experience_level",
                excerpt="Experience: " + experience,
            )
        )
    return RawJob(
        company=config.name,
        source=source,
        source_type="official",
        external_id=row["id"],
        title=row["title"],
        apply_url=apply,
        source_url=row["url"],
        description=description,
        location=", ".join(filter(None, [fields.get("City"), row["country"]])),
        employment_type=row["employment"],
        publication_day=date.fromisoformat(row["published"]),
        minimum_experience_years=minimum,
        experience_evidence=evidence,
        raw_payload={"card": row, "fields": fields},
    )


class TotalEnergiesCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url != SEARCH or config.tenant != "totalenergies":
            raise ValueError("Use the verified TotalEnergies career catalogue and tenant")
        self.source, self.config, self.http = source, config, http
        self.options = SearchOptions(**config.options)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("TotalEnergies scan time budget exceeded") from None

    async def listing(self) -> list[dict[str, str]]:
        combined: dict[str, dict[str, str]] = {}
        for term in self.options.search_terms:
            offset, expected = 0, None
            seen: set[str] = set()
            while True:
                url = (
                    SEARCH
                    + "/?"
                    + urlencode({"search": term, "jobRecordsPerPage": 20, "jobOffset": offset})
                )
                text = await self.http.get_text(url, self.config.request_interval, self.source)
                total, rows = parse_page(text, term, offset, self.options.max_results_per_query)
                if expected is not None and total != expected:
                    raise SourceUnavailable("TotalEnergies catalogue total changed")
                expected = total
                for row in rows:
                    if row["id"] in seen or row["id"] in combined and combined[row["id"]] != row:
                        raise SourceUnavailable(
                            "TotalEnergies repeated page or conflicting vacancy"
                        )
                    seen.add(row["id"])
                    combined[row["id"]] = row
                offset += len(rows)
                if offset == total:
                    break
        return sorted(combined.values(), key=lambda r: r["id"])

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        rows = await self.listing()
        targets = [
            r
            for r in rows
            if any(has(normalize_text(r["title"]), t) for t in self.options.title_terms)
            and not any(
                has(normalize_text(r["title"]), t) for t in self.options.exclude_title_terms
            )
        ]
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("TotalEnergies detail limit exceeded")
        jobs = []
        for row in targets:
            text = await self.http.get_text(row["url"], self.config.request_interval, self.source)
            jobs.append(parse_detail(text, row, self.config, self.source))
        if await self.listing() != rows:
            raise SourceUnavailable("TotalEnergies catalogue changed during collection")
        return Collection(
            jobs=jobs, complete=False, requests=self.http.counts[self.source] - before
        )
