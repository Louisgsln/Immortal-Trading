"""Employer mission excerpts from audited sections, without eligibility inference."""

import html

from trading_radar.description_sections import labelled_lists, normalize_heading, visible_text
from trading_radar.html_page import Document, Element
from trading_radar.models import Job

_HEADINGS = {
    "citi": {"responsibilities", "key responsibilities", "what you'll do"},
    "drw": {
        "responsibilities",
        "key responsibilities",
        "core responsibilities",
        "what you'll be working on",
        "what you'll do",
        "how you will make an impact",
        "what you would do",
        "what you will do",
        "what you'll do in this role",
    },
    "imc": {
        "your core responsibilities",
        "core responsibilities",
        "key responsibilities",
        "your core responsibilties",  # Employer spelling in two audited descriptions.
    },
    "jump_trading": {"what you'll do", "what you will do"},
    "goldman_sachs": {
        "responsibilities",
        "key responsibilities",
        "job responsibilities",
        "role responsibilities",
        "your responsibilities",
        "principal responsibilities",
        "general responsibilities",
        "how you will fulfil your potential",
        "what you will do",
    },
}
_HSBC_SECTIONS = (
    ("purpose of the job", "environment of the job", False),
    ("les grandes lignes", "profil recherché", True),
    (
        "in this role you will",
        "to be successful in this role you should meet the following requirements",
        True,
    ),
)


def _hsbc_section(root: Element) -> tuple[str, list[str]] | None:
    # This portal wraps newline-delimited text in a single paragraph. Both
    # boundaries must be unique: never scan an unbounded remainder of a page.
    lines = [line.strip() for line in visible_text(root).splitlines() if line.strip()]
    labels = [normalize_heading(line) for line in lines]
    matches = []
    for start, end, bullets in _HSBC_SECTIONS:
        if start not in labels:
            continue
        if labels.count(start) != 1 or labels.count(end) != 1:
            return None
        first, last = labels.index(start), labels.index(end)
        if last <= first + 1:
            return None
        body = lines[first + 1 : last]
        if bullets:
            if not body[0].startswith("* "):
                return None
            items: list[str] = []
            for line in body:
                if line.startswith("* "):
                    items.append(line[2:])
                else:
                    items[-1] += " " + line
        else:
            items = [" ".join(body)]
        matches.append((lines[first], items))
    return matches[0] if len(matches) == 1 else None


def mission_excerpts(job: Job) -> dict | None:
    """Return up to three complete items from one unambiguous employer section.

    None means unsupported or unrecognized, never an absence of responsibilities.
    Long items are not selectively dropped: retain the original description instead.
    """
    if job.source not in _HEADINGS and job.source != "hsbc_professionals":
        return None
    root = Document(html.unescape(job.description)).root
    if job.source == "hsbc_professionals":
        section = _hsbc_section(root)
        if section is None:
            return None
        heading, items = section
    else:
        sections = list(labelled_lists(root, _HEADINGS[job.source]))
        if len(sections) != 1:
            return None
        heading, node = sections[0]
        items = [
            visible_text(child)
            for child in node.children
            if isinstance(child, Element) and child.tag == "li"
        ]
    excerpts = [" ".join(item.split()) for item in items[:3]]
    if not excerpts or any(not item or len(item) > 1500 for item in excerpts):
        return None
    return {"heading": heading, "excerpts": excerpts}
