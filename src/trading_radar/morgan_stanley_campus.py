"""Morgan Stanley's public Oleeo Global Programs board. No events or login pages."""

import asyncio
import html
import re
from urllib.parse import parse_qs, urljoin, urlsplit

from trading_radar.config import Company
from trading_radar.description_sections import visible_text
from trading_radar.html_page import Document, Element, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, CollectionConflict, RawJob
from trading_radar.normalizer import has, normalize_text
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import SelectionAudit

BOARD = "https://morganstanley.tal.net/vx/lang-en-GB/candidate/jobboard/vacancy/1/adv"
_DETAIL = re.compile(
    r"/vx/lang-en-GB/(?:mobile-\d+/)?(?:brand-\d+/)?(?:xf-[a-zA-Z0-9]+/)?candidate/so/pm/1/pl/1/opp/(\d+)-([^/]+)/en-GB"
)
_PUBLIC_TAGS = {"p", "ul", "ol", "li", "strong", "b", "em", "br", "h2", "h3", "h4"}


class CampusTitleConflict(SourceUnavailable):
    """An unconfirmed detail title must never become an accepted posting."""


def public_html(node: Element) -> str:
    if (
        node.tag in {"script", "style", "template", "noscript", "form", "input"}
        or "hidden" in node.attrs
    ):
        return ""
    content = "".join(
        public_html(c) if isinstance(c, Element) else html.escape(c) for c in node.children
    )
    if node.tag == "br":
        return "<br>"
    return f"<{node.tag}>{content}</{node.tag}>" if node.tag in _PUBLIC_TAGS else content


def canonical_detail(url: str, identifier: str) -> str:
    parts = urlsplit(urljoin(BOARD, url))
    match = _DETAIL.fullmatch(parts.path)
    if (
        parts.scheme != "https"
        or parts.netloc != "morganstanley.tal.net"
        or parts.query
        or parts.fragment
        or not match
        or match[1] != identifier
    ):
        raise SourceUnavailable("Morgan Stanley campus detail link is invalid")
    return f"https://morganstanley.tal.net/vx/lang-en-GB/candidate/so/pm/1/pl/1/opp/{match[1]}-{match[2]}/en-GB"


class MorganStanleyCampusCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if config.career_url.rstrip("/") != BOARD:
            raise ValueError("Only the public Morgan Stanley Global Programs board is supported")
        self.source, self.config, self.http = source, config, http
        self.options = SearchOptions(**config.options)

    async def fetch(self, url: str) -> str:
        return await self.http.get_text(url, self.config.request_interval, self.source)

    async def collect(self) -> Collection:
        try:
            async with asyncio.timeout(self.options.max_scan_seconds):
                return await self._collect()
        except TimeoutError:
            raise SourceUnavailable("Morgan Stanley campus scan time budget exceeded") from None

    def listing(self, text: str, offset: int):
        nodes = list(Document(text).root.walk())
        headings = with_class(nodes, "job-board-title")
        metas = with_class(nodes, "results_meta")
        lists = [n for n in nodes if n.attrs.get("id") == "results_list"]
        counts = re.findall(r"\b(\d+) results match\b", clean(metas[0])) if len(metas) == 1 else []
        if (
            not headings
            or {clean(heading) for heading in headings} != {"Global Programs"}
            or len(counts) != 1
            or len(lists) != 1
        ):
            raise SourceUnavailable("Morgan Stanley campus board structure is invalid")
        total = int(counts[0])
        if total > self.options.max_results_per_query:
            raise SourceUnavailable("Morgan Stanley campus result limit exceeded")
        rows = [n for n in lists[0].walk() if n.tag == "tr" and "data-oppid" in n.attrs]
        if len(rows) != min(50, max(0, total - offset)):
            raise SourceUnavailable("Morgan Stanley campus page is incomplete")
        entries = []
        for row in rows:
            identifier = row.attrs["data-oppid"]
            links = [n for n in with_class(row.walk(), "subject") if n.tag == "a"]
            cells = [n for n in row.children if isinstance(n, Element) and n.tag == "td"]
            if not re.fullmatch(r"\d+", identifier) or len(links) != 1 or len(cells) != 2:
                raise SourceUnavailable("Morgan Stanley campus listing is malformed")
            title = clean(links[0])
            if not title or normalize_text(title) != normalize_text(
                row.attrs.get("data-title", "")
            ):
                raise SourceUnavailable("Morgan Stanley campus listing title disagrees")
            entries.append(
                (
                    identifier,
                    title,
                    clean(cells[1]),
                    canonical_detail(links[0].attrs.get("href", ""), identifier),
                )
            )
        next_links = [
            a
            for n in with_class(nodes, "next_links")
            for a in n.walk()
            if a.tag == "a" and clean(a) == "Next page"
        ]
        if offset + len(rows) < total:
            if len(next_links) != 1:
                raise SourceUnavailable("Morgan Stanley campus next page is missing")
            url = urlsplit(urljoin(BOARD, next_links[0].attrs.get("href", "")))
            if (
                url.scheme != "https"
                or url.netloc != "morganstanley.tal.net"
                or url.path != urlsplit(BOARD).path
                or url.fragment
                or parse_qs(url.query) != {"start": [str(offset + len(rows))]}
            ):
                raise SourceUnavailable("Morgan Stanley campus next page is invalid")
        elif next_links:
            raise SourceUnavailable("Morgan Stanley campus unexpected next page")
        return total, entries

    async def detail(self, entry) -> RawJob:
        identifier, title, location, url = entry
        nodes = list(Document(await self.fetch(url)).root.walk())
        headings = [n for n in nodes if n.tag == "h1"]
        if not headings or {normalize_text(clean(heading)) for heading in headings} != {
            normalize_text(title)
        }:
            raise CampusTitleConflict("Morgan Stanley campus detail title disagrees")
        fields = {}
        for group in with_class(nodes, "form-group"):
            if "data-field_id" not in group.attrs:
                continue
            labels = with_class(group.walk(), "hform_lbl_text")
            values = with_class(group.walk(), "form-control-static")
            if len(labels) != 1 or len(values) != 1:
                raise SourceUnavailable("Morgan Stanley campus detail field is malformed")
            key = clean(labels[0])
            if key in fields:
                raise SourceUnavailable("Morgan Stanley campus duplicate detail field")
            fields[key] = values[0]
        if not all(k in fields for k in ("City", "Job description", "Program")):
            raise SourceUnavailable("Morgan Stanley campus detail is incomplete")
        if normalize_text(clean(fields["City"])) != normalize_text(location):
            raise SourceUnavailable("Morgan Stanley campus location changed during scan")
        description = public_html(fields["Job description"])
        if not visible_text(fields["Job description"]).strip():
            raise SourceUnavailable("Morgan Stanley campus description is empty")
        # Structured programme facts are public; never copy session/form data.
        for key in ("Program", "Education Level", "Business Unit"):
            if key in fields:
                description += (
                    f"<p><strong>{html.escape(key)}:</strong> {html.escape(clean(fields[key]))}</p>"
                )
        return RawJob(
            company=self.config.name,
            source=self.source,
            source_type="official",
            title=title,
            external_id=identifier,
            apply_url=url,
            source_url=url,
            location=location,
            description=description,
            employment_type=clean(fields["Program"]),
        )

    async def _collect(self) -> Collection:
        before = self.http.counts[self.source]
        candidates, expected, offset = {}, None, 0
        while expected is None or offset < expected:
            total, entries = self.listing(
                await self.fetch(BOARD + (f"?start={offset}" if offset else "")), offset
            )
            if expected is not None and total != expected:
                raise SourceUnavailable("Morgan Stanley campus total changed during pagination")
            expected = total
            for entry in entries:
                if entry[0] in candidates:
                    raise SourceUnavailable("Morgan Stanley campus repeated posting")
                candidates[entry[0]] = entry
            offset += len(entries)
        audit, targets = SelectionAudit("public_catalogue"), []
        for entry in candidates.values():
            title = normalize_text(entry[1])
            selected = (
                not self.options.title_terms or any(has(title, t) for t in self.options.title_terms)
            ) and not any(has(title, t) for t in self.options.exclude_title_terms)
            audit.record(
                None if selected else "outside_title_scope", title=entry[1], identifier=entry[0]
            )
            if selected:
                targets.append(entry)
        if len(targets) > self.options.max_details:
            raise SourceUnavailable("Morgan Stanley campus detail limit exceeded")
        jobs, conflicts = [], []
        first_conflict = None
        for entry in targets:
            try:
                jobs.append(await self.detail(entry))
            except CampusTitleConflict as exc:
                first_conflict = first_conflict or exc
                conflicts.append(
                    CollectionConflict(
                        external_id=entry[0],
                        urls=[BOARD, entry[3]],
                        fields=["title"],
                    )
                )
        if targets and not jobs and first_conflict:
            raise first_conflict
        return Collection(
            jobs=jobs,
            scope_complete=not conflicts,
            conflicts=conflicts,
            requests=self.http.counts[self.source] - before,
            selection=audit.summary(),
        )
