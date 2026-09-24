"""Conservative lower bounds for plain, explicit candidate experience ranges."""

import re
import unicodedata

_RANGE = re.compile(
    r"(?<![\w.+\-–—])(?P<low>\d{1,2})[ \t]*[-–—][ \t]*(?P<high>\d{1,2})"
    r"[ \t]+years?[ \t]+(?:of[ \t]+)?"
    r"(?:(?:prior|relevant|related|professional|work|working|trading|structuring|"
    r"options|securities|financing|financial|markets|legal|progressive|technical)"
    r"[ \t]+){0,3}experience\b",
    re.IGNORECASE,
)
_SECTION = re.compile(
    r"\b(?P<optional>(?:recommended|preferred|desirable|optional)\s+"
    r"(?:qualifications|requirements|skills)|nice\s+to\s+have)\b"
    r"|\b(?P<business>about\s+(?:us|the\s+(?:company|firm))|our\s+(?:company|history))\b"
    r"|\b(?P<required>(?:(?:basic|minimum|required|essential|other|skills\s+and)\s+)?"
    r"qualifications|requirements|about\s+you|who\s+you\s+are|"
    r"your\s+skills\s+and\s+experience|what\s+(?:we(?:'re|\s+are)\s+looking\s+for|"
    r"you\s+bring\s+to\s+the\s+team|you(?:'ll|\s+will)\s+bring\s+to\s+the\s+role))\b",
    re.IGNORECASE,
)
_OPTIONAL = re.compile(
    r"\b(?:preferred|preferable|preferably|recommended|desirable|desired|ideally|ideal|"
    r"typically|typical|usually|usual|approximately|roughly|around|optional|advantageous|"
    r"nice\s+to\s+have|a\s+plus|an?\s+(?:advantage|asset)|"
    r"not\s+(?:required|needed|essential|necessary|mandatory|a\s+must))\b",
    re.IGNORECASE,
)
_UPPER_BOUND = re.compile(
    r"\b(?:up\s+to|less\s+than|at\s+most|no\s+more\s+than|maximum(?:\s+of)?)\b",
    re.IGNORECASE,
)
_NEGATED = re.compile(
    r"\b(?:without|need\s+not|must\s+not|do(?:es)?\s+not\s+(?:need|require)|"
    r"don't\s+need|no\s+(?:need|requirement)\s+for|not\s+necessary\s+to\s+have)\b",
    re.IGNORECASE,
)
_BUSINESS = re.compile(
    r"\b(?:(?:our|the|this)\s+(?:firm|company|business|team|organization)|"
    r"we|he|she|they)\s+(?:has|have|brings?|offers?|with|holds?)\b"
    r"|\b(?:combined|collective|collectively|company\s+history)\b",
    re.IGNORECASE,
)
_ALTERNATIVE = re.compile(
    r"\b(?:either|alternatively|instead|in\s+lieu|substitut\w*|waiv\w*)\b"
    r"|\bor\s+(?:(?:an?|the)\s+)?(?:\d|(?:no|zero)\s+experience|"
    r"equivalent\s+(?:work\s+)?experience|"
    r"(?:bachelor|master|doctoral|doctorate|phd|degree|bsc|msc|bs|ms|mba|jd)\b)",
    re.IGNORECASE,
)
# Official ATS descriptions sometimes flatten bullets into spaces. Only these
# capitalized starts terminate a range's trailing qualifier, never arbitrary
# uppercase product names. Section headers are tracked separately across lines.
_NEXT_ITEM = re.compile(
    r"\s+(?=(?:Strong|Excellent|Demonstrated|Demonstrates|Knowledge|Ability|"
    r"Advance|Advanced|Proficiency|Consistently|Communications|Communication|"
    r"Must|Have|Bachelor|Master)\b)"
)
_BOUNDARY = re.compile(r"[.;!?\r\n•]+")


def plain_range_experience_years(text: str) -> list[int]:
    """Read N–M years of experience in candidate requirement context.

    Preserve original punctuation, case and both endpoints. Optional sections
    remain optional across flattened bullets until a recognized section changes
    their scope. Unknown phrasing is deliberately left unclassified. Existing
    ``N+ years`` and additive degree rules remain the responsibility of callers.
    """
    text = unicodedata.normalize("NFKC", text).replace("’", "'")
    sections = list(_SECTION.finditer(text))
    minima: list[int] = []
    for match in _RANGE.finditer(text):
        low, high = int(match["low"]), int(match["high"])
        if low > high:
            continue
        section = next((s for s in reversed(sections) if s.end() <= match.start()), None)
        if section is not None and section.lastgroup != "required":
            continue
        boundaries = list(_BOUNDARY.finditer(text, 0, match.start()))
        start = boundaries[-1].end() if boundaries else 0
        if section is not None:
            start = max(start, section.end())
        ending = _BOUNDARY.search(text, match.end())
        stop = ending.start() if ending else len(text)
        before = text[start : match.start()]
        after = text[match.end() : stop]
        following_item = _NEXT_ITEM.search(after)
        if following_item and re.search(
            r"\bor\s+(?:an?\s+)?$", after[: following_item.end()], re.IGNORECASE
        ):
            following_item = None
        attached_after = after[: following_item.start()] if following_item else after
        full_clause = before + match[0] + attached_after
        if _ALTERNATIVE.search(full_clause) or re.match(
            r"\s*(?:[.;\r\n]+\s*)?(?:or|alternatively|instead)\b", text[stop:], re.IGNORECASE
        ):
            continue
        if _BUSINESS.search(full_clause) or _UPPER_BOUND.search(before) or _NEGATED.search(before):
            continue
        if _OPTIONAL.search(before) or _OPTIONAL.search(attached_after):
            continue
        if (
            section is None
            and before.strip(" :\t-–—")
            and not re.search(
                r"\b(?:you\s+(?:have|bring)|candidates?\s+(?:have|with)|"
                r"must\s+have|requires?|required|minimum(?:\s+of)?|at\s+least)\s*$",
                before,
                re.IGNORECASE,
            )
        ):
            continue
        minima.append(low)
    return list(dict.fromkeys(minima))
