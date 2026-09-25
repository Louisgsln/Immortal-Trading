"""Read-only degree mentions in audited DRW/IMC candidate qualification lists.

Mentions are not eligibility decisions or minimum degree requirements. Full list
items preserve alternatives, preferences, negations and graduation conditions.
"""

import html
import re

from trading_radar.description_sections import labelled_lists, visible_text
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
_SHORT_DEGREE_CONTEXT = r"\b\.?(?=\s*(?:[,/]|(?:or|and|in|degree|preferably|preferred)\b|$))"
_DEGREES = {
    "bachelor": re.compile(
        r"\b(?i:bachelor(?:['’]s|s)?)\b|\bB\.?S\.?[cC]\b|\bB\.?S" + _SHORT_DEGREE_CONTEXT
    ),
    "master": re.compile(
        r"\b(?i:master(?:['’]s|s|(?=\s+(?:degree|of)\b)))\b|\bM\.?S\.?[cC]\b|\bM\.?S"
        + _SHORT_DEGREE_CONTEXT
    ),
    "doctorate": re.compile(r"\bPh\.?D\b|\bdoctorate\b|\bdoctoral\s+degree\b", re.I),
}


def education_mentions(job: Job) -> dict:
    """Return detached observations; never write to a Job or infer a score."""
    result: dict = {"levels": [], "evidence": []}
    if job.source not in _HEADINGS:
        return result
    document = Document(html.unescape(job.description))
    for heading, section in labelled_lists(document.root, _HEADINGS[job.source]):
        for item in section.children:
            if not isinstance(item, Element) or item.tag != "li":
                continue
            excerpt = " ".join(visible_text(item).split())
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
