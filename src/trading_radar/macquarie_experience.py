"""Provenance for the narrowly audited Macquarie sales-trading qualification."""

import re

from trading_radar.html_page import Document, Element
from trading_radar.models import ExperienceEvidence

_REQUIREMENT = re.compile(
    r"^(?P<years>0|[1-9][0-9]?)\s+years[’']?\s+of\s+experience\s+in\s+sales\s+trading\b",
    re.IGNORECASE,
)
# The captured 23225 requirement is followed by a separate flattened bullet.
# Its later degree preference does not qualify the preceding years requirement.
_NEXT_ITEM = re.compile(r"\s+(?=Proven\s+ability\b)")
_UNCERTAIN = re.compile(
    r"\b(?:preferred|preferable|preferably|recommended|desirable|desired|ideally|ideal|"
    r"typically|usually|approximately|roughly|around|optional|advantageous|"
    r"nice\s+to\s+have|a\s+plus|an?\s+(?:advantage|asset)|"
    r"not|without|no\s+(?:need|requirement)|up\s+to|less\s+than|at\s+most|"
    r"no\s+more\s+than|maximum|either|alternatively|instead|in\s+lieu|"
    r"substitut\w*|waiv\w*|contract|placement|duration|tenure|founded|established|"
    r"(?:our|the|this)\s+(?:company|firm|team|organization)|"
    r"(?:we|he|she|they)\s+(?:have|has|bring|brings))\b"
    r"|\bor\s+(?:(?:an?|the)\s+)?(?:\d|(?:no|zero)\s+experience|"
    r"equivalent\s+(?:work\s+)?experience|"
    r"(?:bachelor|master|doctoral|doctorate|phd|degree|bsc|msc|bs|ms|mba|jd)\b)",
    re.IGNORECASE,
)


def _paragraphs(node: Element):
    if node.tag in {"script", "style", "template"}:
        return
    if node.tag == "p":
        # A real paragraph boundary is necessary. Plain descriptions and arbitrary
        # sentence fragments cannot establish the audited qualification position.
        yield " ".join(node.text(without_headings=True).split())
        return
    for child in node.children:
        if isinstance(child, Element):
            yield from _paragraphs(child)


def macquarie_sales_trading_evidence(content: str) -> list[ExperienceEvidence]:
    """Return only explicit paragraph-leading professional sales-trading years.

    Preserve the original rendered clause (including apostrophes and case).
    Neither generic plain ``N years`` language nor ranges are added to this rule.
    The caller must scope this source-specific helper to Macquarie descriptions.
    """
    evidence = []
    for paragraph in _paragraphs(Document(content).root):
        match = _REQUIREMENT.match(paragraph)
        if not match:
            continue
        excerpt = _NEXT_ITEM.split(paragraph, maxsplit=1)[0].strip()
        if _UNCERTAIN.search(excerpt):
            continue
        item = ExperienceEvidence(
            minimum_years=int(match["years"]),
            kind="professional",
            origin="description",
            method="macquarie_sales_trading_experience",
            excerpt=excerpt,
        )
        if item not in evidence:
            evidence.append(item)
    return evidence
