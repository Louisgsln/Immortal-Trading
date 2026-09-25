"""Read-only degree mentions in audited DRW/IMC candidate qualification lists.

Mentions are not eligibility decisions or minimum degree requirements. Full list
items preserve alternatives, preferences, negations and graduation conditions.
"""

import html
import re

from trading_radar.html_page import Document, Element
from trading_radar.models import Job

_HEADINGS = {
    "drw": {
        "key skills",
        "preferred background",
        "qualifications and skills",
        "required experience",
        "required qualifications",
        "requirements",
        "what we are looking for",
        "what you bring to the team",
        "what you will need",
        "what's needed in this role",
        "you'll feel right at home if you",
    },
    "imc": {"skills and experience", "your skills and experience"},
}
_DEGREES = {
    "bachelor": re.compile(r"\b(?i:bachelor(?:['’]s|s)?)\b|\bB\.?S\.?c?\b"),
    "master": re.compile(r"\b(?i:master(?:['’]s|s|(?=\s+(?:degree|of)\b)))\b|\bM\.?S\.?c?\b"),
    "doctorate": re.compile(r"\bPh\.?D\b|\bdoctorate\b|\bdoctoral\s+degree\b", re.I),
}
_HIDDEN = {"script", "style", "template", "noscript"}


def _text(node: Element) -> str:
    if node.tag in _HIDDEN or "hidden" in node.attrs:
        return ""
    return " ".join(
        _text(child) if isinstance(child, Element) else child for child in node.children
    )


def _heading(text: str) -> str:
    return " ".join(text.lower().replace("’", "'").replace("&", "and").split()).strip(" :.…")


def _lists(node: Element, headings: set[str]):
    if node.tag in _HIDDEN or "hidden" in node.attrs:
        return
    previous = ""
    for child in node.children:
        if isinstance(child, str):
            if child.strip():
                previous = ""
            continue
        text = " ".join(_text(child).split())
        if child.tag in {"ul", "ol"} and _heading(previous) in headings:
            yield previous, child
        if text:
            previous = text if child.tag in {"p", "h2", "h3", "h4", "strong"} else ""
        yield from _lists(child, headings)


def education_mentions(job: Job) -> dict:
    """Return detached observations; never write to a Job or infer a score."""
    result: dict = {"levels": [], "evidence": []}
    if job.source not in _HEADINGS:
        return result
    document = Document(html.unescape(job.description))
    for heading, section in _lists(document.root, _HEADINGS[job.source]):
        for item in section.children:
            if not isinstance(item, Element) or item.tag != "li":
                continue
            excerpt = " ".join(_text(item).split())
            if not excerpt or len(excerpt) > 1500:
                continue
            levels = [key for key, pattern in _DEGREES.items() if pattern.search(excerpt)]
            if not levels and re.search(
                r"\bdegree\s+(?:in|from|required|preferred)\b", excerpt, re.I
            ):
                levels = ["unspecified_level"]
            if not levels or any(e["excerpt"] == excerpt for e in result["evidence"]):
                continue
            result["evidence"].append({"heading": heading, "excerpt": excerpt, "levels": levels})
            result["levels"].extend(level for level in levels if level not in result["levels"])
    return result
