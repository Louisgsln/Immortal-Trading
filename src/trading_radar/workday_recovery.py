"""Verify opaque CXS references against their employer's public career pages.

Only an explicitly identified, out-of-scope title can close a coverage gap.
Missing, unpublished or ambiguous pages remain gaps, never closed vacancies.
"""

import json
import re
from urllib.parse import urlsplit

from trading_radar.html_page import Document, clean
from trading_radar.http import HTTPClient, SourceUnavailable

CITI = "https://jobs.citi.com"
BP = "https://careers.bp.com"
SITES = {
    "citi": "https://citi.wd5.myworkdayjobs.com/2",
    "bp": "https://bpinternational.wd3.myworkdayjobs.com/bpCareers",
}


def citi_operations_reference(payload: object, reference: str) -> bool:
    """An exact, single-reference public query explicitly classifies the role.

    This audited Citi category is transaction processing, outside the front
    office target. No inferred title and no generic exclusion of other families.
    """
    if not isinstance(payload, dict) or type(payload.get("total")) is not int:
        return False
    if payload["total"] != 1 or payload.get("jobPostings") != [{"bulletFields": [reference]}]:
        return False
    facets = payload.get("facets")
    if not isinstance(facets, list):
        return False
    families = [
        f for f in facets if isinstance(f, dict) and f.get("facetParameter") == "jobFamilyGroup"
    ]
    if len(families) != 1:
        return False
    values = families[0].get("values")
    return (
        isinstance(values, list)
        and len(values) == 1
        and isinstance(values[0], dict)
        and type(values[0].get("count")) is int
        and values
        == [
            {
                "descriptor": "Operations - Transaction Services",
                "id": "e32326e1708d01add154fc0c1201f6c0",
                "count": 1,
            }
        ]
    )


def posting(text: str) -> dict | None:
    records = []
    for node in Document(text).root.walk():
        if node.tag == "script" and node.attrs.get("type") == "application/ld+json":
            try:
                value = json.loads(node.text())
            except ValueError:
                return None
            if isinstance(value, dict) and value.get("@type") == "JobPosting":
                records.append(value)
    if len(records) != 1 or not isinstance(records[0].get("title"), str):
        return None
    return records[0] if records[0]["title"].strip() else None


def citi_result(text: str, reference: str) -> str | None:
    sections = [n for n in Document(text).root.walk() if n.attrs.get("id") == "search-results"]
    if len(sections) != 1 or any(
        sections[0].attrs.get(k) != v
        for k, v in {
            "data-keywords": reference,
            "data-total-results": "1",
            "data-total-job-results": "1",
            "data-total-pages": "1",
            "data-current-page": "1",
        }.items()
    ):
        return None
    links = {
        n.attrs.get("href", "")
        for n in sections[0].walk()
        if n.tag == "a" and n.attrs.get("href", "").startswith("/job/")
    }
    if len(links) != 1:
        return None
    path = links.pop()
    return CITI + path if re.fullmatch(r"/job/[a-z0-9-]+/[a-z0-9-]+/287/[0-9]+", path) else None


def verified_title(text: str, source: str, reference: str, url: str) -> str | None:
    info = posting(text)
    if info is None:
        return None
    nodes = list(Document(text).root.walk())
    links = [n.attrs.get("href", "") for n in nodes if n.tag == "a"]
    if source == "citi":
        if info.get("identifier") != reference or info.get("url") != url:
            return None
        # The employer's page explicitly links this exact requisition in CXS.
        paths = set()
        for link in links:
            parts = urlsplit(link)
            if (parts.scheme, parts.netloc) == ("https", "citi.wd5.myworkdayjobs.com"):
                if (
                    re.fullmatch(
                        r"/2/job/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+_" + reference + r"/apply", parts.path
                    )
                    and not parts.query
                    and not parts.fragment
                ):
                    paths.add(parts.path)
        titles = [clean(n) for n in nodes if n.tag == "h1"]
        if len(paths) != 1 or titles != [info["title"]]:
            return None
    elif source == "bp":
        organization = info.get("hiringOrganization")
        if (
            url != BP + "/job-description/" + reference
            or not isinstance(organization, dict)
            or organization.get("name") != "bp"
        ):
            return None
        # BP omits identifier.value from JSON-LD. Its published application link
        # contains the exact requisition; never infer it from the title alone.
        paths = {
            link
            for link in links
            if re.fullmatch(r"/job/apply/[a-z0-9-]+-" + reference.lower() + r"\??", link)
        }
        if len(paths) != 1:
            return None
    else:
        return None
    return info["title"].strip()


async def public_reference_title(
    source: str, site: str, reference: str, http: HTTPClient, interval: float
) -> str | None:
    if SITES.get(source) != site or not re.fullmatch(
        r"[0-9]{8}" if source == "citi" else r"RQ[0-9]{6}", reference
    ):
        return None
    try:
        if source == "citi":
            text = await http.get_text(CITI + "/search-jobs?k=" + reference, interval, source)
            url = citi_result(text, reference)
            if url is None:
                return None
        else:
            url = BP + "/job-description/" + reference
        text = await http.get_text(url, interval, source)
        return verified_title(text, source, reference, url)
    except SourceUnavailable:
        # Access restrictions never justify dropping a gap or another valid job.
        return None
