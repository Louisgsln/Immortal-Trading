"""Resolve BNP aliases only against their shared, public recruitment page."""

import html
import re
from urllib.parse import parse_qs, urlsplit

from trading_radar.html_page import Document, clean, with_class
from trading_radar.models import RawJob
from trading_radar.normalizer import plain_text


def recruitment_target(text: str) -> tuple[str, str] | None:
    targets = set()
    for node in Document(text).root.walk():
        if node.tag != "a" or clean(node) != "Postuler":
            continue
        url = node.attrs.get("href", "")
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        if (
            parts.scheme != "https"
            or parts.netloc != "bwelcome.hr.bnpparibas"
            or parts.path
            not in {"/en_US/externalcareers/JobDetails", "/fr_FR/externalcareers/JobDetails"}
            or parts.fragment
            or set(query) - {"jobId", "source"}
            or len(query.get("jobId", [])) != 1
            or not re.fullmatch(r"[1-9][0-9]{0,12}", query["jobId"][0])
        ):
            return None
        targets.add((query["jobId"][0], url))
    return next(iter(targets)) if len(targets) == 1 else None


def matching_alias(text: str, identifier: str, aliases: list[RawJob]) -> RawJob | None:
    nodes = list(Document(text).root.walk())
    canonicals = [
        n.attrs.get("href", "")
        for n in nodes
        if n.tag == "link" and n.attrs.get("rel") == "canonical"
    ]
    if len(canonicals) != 1:
        return None
    canonical = urlsplit(canonicals[0])
    if (
        canonical.scheme != "https"
        or canonical.netloc != "bwelcome.hr.bnpparibas"
        or not re.fullmatch(
            r"/en_US/externalcareers/JobDetail/[A-Za-z0-9-]+/" + re.escape(identifier),
            canonical.path,
        )
        or canonical.query
        or canonical.fragment
    ):
        return None
    titles = with_class(nodes, "title--banner")
    refs = []
    for field in with_class(nodes, "article__content__view__field"):
        labels = with_class(field.walk(), "article__content__view__field__label")
        values = with_class(field.walk(), "article__content__view__field__value")
        if len(labels) == 1 and clean(labels[0]) == "Ref #":
            if len(values) != 1:
                return None
            refs.append(clean(values[0]))
    descriptions = [
        node
        for node in nodes
        if node.tag == "article"
        and [clean(n) for n in node.walk() if n.tag == "h2"] == ["Description"]
    ]
    if len(titles) != 1 or len(descriptions) != 1 or refs != [str(aliases[0].external_id)]:
        return None
    bodies = with_class(descriptions[0].walk(), "article__content")
    if len(bodies) != 1 or not clean(bodies[0]):
        return None

    def comparable(value: str) -> str:
        return "".join(html.unescape(value).split())

    matches = [
        job
        for job in aliases
        if str(job.external_id) == refs[0]
        and comparable(job.title) == comparable(clean(titles[0]))
        and comparable(plain_text(job.description)) == comparable(clean(bodies[0]))
    ]
    return matches[0] if len(matches) == 1 else None
