"""Read-only degree mentions in audited employer qualification sections.

Mentions are not eligibility decisions or minimum degree requirements. Full list
items preserve alternatives, preferences, negations and graduation conditions.
"""

import html
import re
from collections.abc import Iterator

from trading_radar.description_sections import labelled_lists, normalize_heading, visible_text
from trading_radar.html_page import Document, Element
from trading_radar.models import Job
from trading_radar.ubs_sections import bullet_items, field_lines

_HEADINGS = {
    "macquarie": set(),
    "credit_agricole_cib": set(),
    "societe_generale": set(),
    "bnp_paribas": {
        "profile and skills to success",
        "to be considered for the placement, you will",
        "what is required for you to succeed?",
        "your profile",
        "essential",
        "technical and behavioral competencies",
        "requirements",
    },
    "ubs_professionals": set(),
    "barclays": {"essential skills/basic qualifications"},
    "deutsche_bank": {
        "your skills and experience",
        "skills you'll need",
        "skills that will help you excel",
    },
    "morgan_stanley": {
        "qualifications",
        "requirements",
        "what you'll bring to the role",
        "skills desirable",
    },
    "citi": {"education", "qualifications", "recommended qualifications"},
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
    "jump_trading": {"skills you'll need", "skills you will need"},
    "goldman_sachs": {
        "qualifications",
        "basic qualifications",
        "preferred qualifications",
        "required qualifications",
        "required qualifications and skills",
        "preferred qualifications and skills",
        "basic qualifications and preferred qualifications",
    },
}
_SHORT_DEGREE_CONTEXT = r"\b\.?(?=\s*(?:[,/]|(?:or|and|in|degree|preferably|preferred)\b|$))"
_UNSPECIFIED_DEGREE = re.compile(
    r"\bdegree\s+(?:in|from|required|preferred)\b"
    r"|\beducated\s+to\s+(?:a\s+)?degree\s+level\b"
    r"|\bundergraduate\s+degree\b",
    re.I,
)
_BARCLAYS_UNSPECIFIED_DEGREE = re.compile(
    r"\bdegree\s+or\s+expected\s+degree\b"
    r"|\byear\s+of\s+your\s+degree\b"
    r"|\bpost[- ]?graduate\s+degree\b",
    re.I,
)
_UBS_UNSPECIFIED_DEGREE = re.compile(r"\b(?:university|law|graduate)\s+degree\b", re.I)
_BNP_MASTER = re.compile(r"^master\s+in\s+\w", re.I)
_SG_PROFILE = re.compile(r"^(Et si c[’']était vous\s*\?|Profile required)\s+(.+)$", re.I)
_SG_MASTER = re.compile(r"\bde\s+type\s+master\b", re.I)
_BAC = re.compile(r"\bbac\s*\+\s*(4\s*/\s*5|[45])(?!\w|\s*/)", re.I)
_CA_BAC5 = re.compile(r"bac\s*\+\s*5\s*/\s*M2\s+et\s+plus", re.I)
_MACQUARIE_UNSPECIFIED = re.compile(
    r"\b(?:postgraduate|quantitative)\s+degree\b|\btertiary\s+qualification\b", re.I
)
_DEGREES = {
    "bachelor": re.compile(
        r"\b(?i:bachelor(?:['’]s|s)?)\b|\bB\.?S\.?[cC]\b|\bB\.?S" + _SHORT_DEGREE_CONTEXT
    ),
    "master": re.compile(
        r"\b(?i:master(?:['’]s|s|(?=\s+(?:degree|of|or\s+Ph\.?D)\b)))\b|\bM\.?S\.?[cC]\b|\bM\.?S"
        + _SHORT_DEGREE_CONTEXT
        + r"|\b(?i:bachelor\s+or\s+master)(?=\s*\))"
    ),
    "doctorate": re.compile(r"\bPh\.?D\b|\bdoctorate\b|\bdoctoral\s+degree\b", re.I),
}


def _nomura_qualification(root: Element) -> str | None:
    # The collector preserves the visible table as flattened text. Require its
    # complete audited field order and its following responsibilities boundary.
    text = " ".join(visible_text(root).split())
    headings = list(re.finditer(r"\bPosition Specifications\s*:?\s*", text, re.I))
    if len(headings) != 1:
        return None
    context = text[text.rfind(".", 0, headings[0].start()) + 1 : headings[0].start()]
    if re.search(r"\b(?:example|optional|preferred|not)\b|[\"“”]", context, re.I):
        return None
    start = headings[0].end()
    end = re.search(r"\bR\s*ole\s*(?:&|and)\s*Responsibilities\s*:", text[start:], re.I)
    if not end or end.start() > 2100:
        return None
    block = text[start : start + end.start()]
    labels = re.findall(
        r"\b(Corporate Title|Functional Title|Experience(?=\s+\d)|Qualifications?|Requisition No\.?)\b",
        block,
        re.I,
    )
    normalized = [label.lower().rstrip(".") for label in labels]
    expected = ["corporate title", "functional title", "experience", "qualification"]
    if normalized not in (expected, [*expected, "requisition no"]):
        return None
    if normalized[-1] == "requisition no":
        requisition = re.search(r"\s+Requisition No\.\s+\d+\s*$", block, re.I)
        if requisition is None:
            return None
        block = block[: requisition.start()]
    match = re.fullmatch(
        r"Corporate Title\s+.{1,100}?\s+Functional Title\s+.{1,200}?\s+"
        r"Experience\s+.{1,300}?\s+Qualification\s+(?P<excerpt>.{1,1500}?)\s*",
        block,
        re.I,
    )
    if match is None:
        return None
    return match["excerpt"].strip()


def _barclays_qualification(root: Element) -> tuple[str, str] | None:
    # Workday preserves this heading and its body in one paragraph or div,
    # sometimes after other sections. Require a bold heading on its own line,
    # retain the entire remaining block, and never cross a container boundary.
    matches: list[tuple[str, str] | None] = []
    inline = {"br", "span", "i", "em", "a", "b", "strong"}

    def inspect(node: Element) -> None:
        if not visible_text(node).strip():
            return
        children = [c for c in node.children if not isinstance(c, str) or c.strip()]
        for index, child in enumerate(children):
            if not isinstance(child, Element):
                continue
            if (
                node.tag in {"p", "div"}
                and child.tag in {"b", "strong"}
                and normalize_heading(visible_text(child)) == "who we're looking for"
            ):
                heading = " ".join(visible_text(child).split())
                before = children[index - 1] if index else None
                body = children[index + 1 :]
                starts_line = before is None or isinstance(before, Element) and before.tag == "br"
                starts_body = bool(body) and isinstance(body[0], Element) and body[0].tag == "br"
                # A later bold line might be another section or an alternative
                # condition. Reject the block instead of selectively dropping it.
                extra_heading = any(
                    isinstance(item, Element)
                    and item.tag in {"b", "strong"}
                    and isinstance(previous, Element)
                    and previous.tag == "br"
                    for previous, item in zip(body, body[1:], strict=False)
                )
                bounded = all(
                    sub.tag in inline
                    for item in body
                    if isinstance(item, Element)
                    for sub in item.walk()
                )
                excerpt = " ".join(
                    " ".join(
                        visible_text(item) if isinstance(item, Element) else item for item in body
                    ).split()
                )
                matches.append(
                    (heading, excerpt)
                    if starts_line and starts_body and bounded and not extra_heading
                    else None
                )
            inspect(child)

    inspect(root)
    return matches[0] if len(matches) == 1 else None


def _ubs_qualification_items(root: Element) -> Iterator[tuple[str, str]]:
    lines = field_lines(root, "your skills and experience", {"about us"})
    items = bullet_items(lines, mixed=True) if lines is not None else None
    for item in items or []:
        yield "Your skills and experience", item


def _barclays_programme(root: Element) -> tuple[str, str] | None:
    # Tokyo splits the required criteria and the preferred criteria across
    # adjacent paragraphs. Keep the entire required block before its next label.
    label = "to be considered for this program, you must"
    matches: list[tuple[str, str] | None] = []
    children = [n for n in root.children if not isinstance(n, str) or n.strip()]
    for previous, body in zip(children, children[1:], strict=False):
        if not isinstance(previous, Element) or not isinstance(body, Element):
            continue
        if (
            previous.tag != "p"
            or body.tag != "p"
            or "hidden" in body.attrs
            or "hidden" in previous.attrs
        ):
            continue
        parts = [c for c in previous.children if not isinstance(c, str) or c.strip()]
        if not parts or not isinstance(parts[-1], Element) or parts[-1].tag not in {"b", "strong"}:
            continue
        if normalize_heading(visible_text(parts[-1])) != label:
            continue

        # The employer's 'I<b>deally...' spelling crosses an inline boundary.
        def text(node: Element | str) -> str | None:
            if isinstance(node, str):
                return node
            if node.tag == "br" and not node.attrs:
                return "\n"
            if node.tag not in {"b", "strong", "span", "i", "em"} or "hidden" in node.attrs:
                return None
            values = [text(c) for c in node.children]
            return "".join(v for v in values if v is not None) if None not in values else None

        values = [text(c) for c in body.children]
        lines = [
            line.strip()
            for line in "".join(v for v in values if v is not None).splitlines()
            if line.strip()
        ]
        valid = (
            None not in values
            and len(lines) >= 2
            and normalize_heading(lines[-1]) == "ideally, you would also have"
        )
        if valid and all(line.startswith("•") and line[1:].strip() for line in lines[:-1]):
            matches.append(("To be considered for this program, you must:", " ".join(lines[:-1])))
        else:
            matches.append(None)
    return matches[0] if len(matches) == 1 else None


def _bnp_education_field(root: Element) -> tuple[str, str] | None:
    matches = []

    def visible_nodes(node: Element) -> Iterator[Element]:
        if node.tag in {"script", "style", "template", "noscript"} or "hidden" in node.attrs:
            return
        yield node
        for child in node.children:
            if isinstance(child, Element):
                yield from visible_nodes(child)

    for node in visible_nodes(root):
        if node.tag != "p" or "hidden" in node.attrs:
            continue
        # Match the entire visible field, never a mention in another sentence.
        match = re.fullmatch(
            r"Education Level:\s+(.{1,500})", " ".join(visible_text(node).split()), re.I
        )
        if match:
            matches.append(("Education Level", match[1]))
    return matches[0] if len(matches) == 1 else None


def _qualification_items(job: Job) -> Iterator[tuple[str, str]]:
    document = Document(html.unescape(job.description))
    if job.source == "macquarie":
        sections = [
            node
            for node in document.root.children
            if isinstance(node, Element) and "data-macquarie-section" in node.attrs
        ]
        if len(sections) == 1:
            section = sections[0]
            paragraphs = [p for p in section.children if not isinstance(p, str) or p.strip()]
            if (
                section.tag == "section"
                and section.attrs == {"data-macquarie-section": "What you offer"}
                and paragraphs
                and all(
                    isinstance(p, Element)
                    and p.tag == "p"
                    and not p.attrs
                    and all(isinstance(part, str) for part in p.children)
                    for p in paragraphs
                )
            ):
                yield "What you offer", " ".join(visible_text(section).split())
        return
    if job.source == "credit_agricole_cib":
        # Only the collector's verified field survives storage without raw data.
        fields = [
            node
            for node in document.root.children
            if isinstance(node, Element)
            and node.attrs.get("data-ca-field") == "fldapplicantcriteria_educationlevel"
        ]
        if len(fields) == 1:
            field = fields[0]
            label = field.attrs.get("data-ca-label", "")
            if (
                field.tag == "p"
                and set(field.attrs) == {"data-ca-field", "data-ca-label"}
                and normalize_heading(label)
                in {"minimal education level", "niveau d'études minimum"}
                and all(isinstance(part, str) for part in field.children)
            ):
                yield label, " ".join(visible_text(field).split())
        return
    if job.source == "societe_generale":
        # The collector retains the entire profile field in one paragraph,
        # including its visible employer heading. Never split its conditions.
        profiles = [
            match
            for node in document.root.children
            if isinstance(node, Element) and node.tag == "p"
            if (match := _SG_PROFILE.fullmatch(" ".join(visible_text(node).split())))
        ]
        if len(profiles) == 1:
            yield profiles[0][1], profiles[0][2]
        return
    if job.source == "ubs_professionals":
        yield from _ubs_qualification_items(document.root)
        return
    if job.source == "nomura_professionals":
        excerpt = _nomura_qualification(document.root)
        if excerpt:
            yield "Position Specifications → Qualification", excerpt
        return
    if job.source == "barclays":
        inline_section = _barclays_qualification(document.root)
        if inline_section:
            yield inline_section
        programme = _barclays_programme(document.root)
        if programme:
            yield programme
    if job.source == "bnp_paribas":
        bnp_field = _bnp_education_field(document.root)
        if bnp_field:
            yield bnp_field
    for heading, section in labelled_lists(document.root, _HEADINGS.get(job.source, set())):
        for item in section.children:
            if isinstance(item, Element) and item.tag == "li":
                yield heading, " ".join(visible_text(item).split())


def education_mentions(job: Job) -> dict:
    """Return detached observations; never write to a Job or infer a score."""
    result: dict = {"levels": [], "evidence": []}
    if job.source not in _HEADINGS and job.source != "nomura_professionals":
        return result
    for heading, excerpt in _qualification_items(job):
        if not excerpt or len(excerpt) > 1500:
            continue
        levels = [key for key, pattern in _DEGREES.items() if pattern.search(excerpt)]
        if job.source == "credit_agricole_cib" and _CA_BAC5.fullmatch(excerpt):
            levels.append("bac_plus_5")
        if job.source == "bnp_paribas" and _BNP_MASTER.search(excerpt) and "master" not in levels:
            levels.append("master")
        if job.source == "societe_generale":
            if _SG_MASTER.search(excerpt) and "master" not in levels:
                levels.append("master")
        if job.source in {"societe_generale", "credit_agricole_cib"}:
            for match in _BAC.finditer(excerpt):
                for number in match[1].replace(" ", "").split("/"):
                    level = "bac_plus_" + number
                    if level not in levels:
                        levels.append(level)
        if not levels and (
            _UNSPECIFIED_DEGREE.search(excerpt)
            or job.source == "barclays"
            and _BARCLAYS_UNSPECIFIED_DEGREE.search(excerpt)
            or job.source == "ubs_professionals"
            and _UBS_UNSPECIFIED_DEGREE.search(excerpt)
            or job.source == "macquarie"
            and _MACQUARIE_UNSPECIFIED.search(excerpt)
        ):
            levels = ["unspecified_level"]
        if not levels or any(e["excerpt"] == excerpt for e in result["evidence"]):
            continue
        result["evidence"].append({"heading": heading, "excerpt": excerpt, "levels": levels})
        result["levels"].extend(level for level in levels if level not in result["levels"])
    return result
