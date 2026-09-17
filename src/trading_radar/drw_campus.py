"""A narrow DRW campus signal supported by candidate graduation requirements."""

import html
import re

from trading_radar.normalizer import PlainText, normalize_text

_MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
)
_GRADUATION = re.compile(
    r"^\s*(?:a|an)\s+(?:bachelor(?:'s)?|master(?:'s)?|degree)\b"
    r"[^.;!?\r\n]{0,220}?\b(?:and\s+have\s+an?|with\s+an?)\s+"
    r"expected\s+graduation\s+date\s+between\s+"
    rf"{_MONTH}\s+20\d{{2}}\s+and\s+{_MONTH}\s+20\d{{2}}\b",
    re.IGNORECASE,
)
_PLACEMENT = re.compile(r"\b(?:interns?|internships?|apprentices?|apprenticeships?)\b", re.I)


class _Blocks(PlainText):
    """Keep blocks and source line breaks that plain_text deliberately flattens."""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        super().handle_starttag(tag, attrs)
        if not self.hidden and tag in {"br", "p", "li", "h1", "h2", "h3", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        super().handle_endtag(tag)
        if not self.hidden and tag in {"p", "li", "h1", "h2", "h3", "div"}:
            self.parts.append("\n")


def drw_campus_junior(title: str, content: str, fields: dict[str, object]) -> bool:
    """Require campus/full-time metadata and the audited graduation clause.

    Return evidence for seniority only. Do not infer intake/start dates, override
    experience requirements, or classify other employers from this template.
    """
    if (
        fields.get("Website Job Category Filter") != ["Campus"]
        or fields.get("Employment Type") != "Full-time"
        or _PLACEMENT.search(title)
    ):
        return False
    parser = _Blocks()
    parser.feed(html.unescape(content))
    blocks = [
        " ".join(block.split()).replace("’", "'").replace("‘", "'")
        for block in " ".join(parser.parts).splitlines()
        if block.strip()
    ]
    headings = [
        index
        for index, block in enumerate(blocks)
        if normalize_text(block)
        in {
            "what you bring to the team",
            "what do you bring to the team",
            "what you will bring to the team",
        }
    ]
    if len(headings) != 1:
        return False
    heading = headings[0]
    company_start = next(
        (
            index
            for index in range(heading + 1, len(blocks))
            if re.match(r"DRW\s+is\b", blocks[index], re.IGNORECASE)
        ),
        len(blocks),
    )
    # A following placement section describes the role even though it ends the
    # candidate-requirements section. Only the company introduction ends this
    # separate exclusion scope.
    if _PLACEMENT.search(" ".join(blocks[:company_start])):
        return False
    stop = next(
        (
            index
            for index in range(heading + 1, len(blocks))
            if re.match(
                r"(?:DRW\s+is\b|About\b|Benefits\b|What\s+to\s+expect\b|How\s+you\b|"
                r"Preferred\s+Qualifications\b|Nice\s+to\s+Have\b)",
                blocks[index],
                re.IGNORECASE,
            )
        ),
        len(blocks),
    )
    for block in blocks[heading + 1 : stop]:
        for clause in re.split(r"[.;!?\r\n]+", block):
            if re.search(
                r"\b(?:preferred|preferably|ideally|desirable|helpful|optional|"
                r"not\s+(?:required|necessary|essential)|previously|already|had|was)\b",
                clause,
                re.IGNORECASE,
            ):
                continue
            if _GRADUATION.search(clause):
                return True
    return False
