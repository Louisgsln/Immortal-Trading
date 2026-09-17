"""Conservative extraction of experience explicitly added to an academic degree."""

import re
import unicodedata

_DEGREE = r"\b(?:(?:bachelor|master)(?:'s|s)?\s+|university\s+|college\s+|advanced\s+)?degree\b"
_ADDITIVE = re.compile(
    _DEGREE + r"(?P<education>[^.;!?\r\n]{0,180}?)\s+plus\s+"
    r"(?P<low>\d{1,2})(?:\s*[-–—]\s*(?P<high>\d{1,2}))?\s*\+?\s+years?\s+"
    r"(?:of\s+)?(?:(?:relevant|progressive|professional|related|technical|work|working)\s+){0,3}"
    r"experience\b",
    re.IGNORECASE,
)
_OPTIONAL = re.compile(
    r"\b(?:preferred|preferable|desirable|desired|advantageous|optional|ideally|preferably|"
    r"nice\s+to\s+have|not\s+(?:required|essential|necessary|mandatory)|"
    r"a\s+plus|an?\s+(?:advantage|asset))\b",
    re.IGNORECASE,
)
_ALTERNATIVE = re.compile(
    r"\b(?:either|alternatively|instead|in\s+lieu|substitut\w*|waiv\w*)\b"
    r"|\bor\s+(?:(?:an?|the)\s+)?(?:\d|(?:no|zero)\s+experience|"
    r"equivalent\s+(?:work\s+)?experience|"
    r"(?:bachelor|master|doctoral|doctorate|phd|degree|bsc|msc|bs|ms|mba|jd)\b)",
    re.IGNORECASE,
)


def degree_experience_years(text: str) -> list[int]:
    """Read only unambiguous ``degree … plus N years … experience`` clauses.

    Bound the degree-to-plus gap and experience modifiers. Sentence, semicolon
    and line boundaries are never crossed. Ambiguous education alternatives or
    preferences anywhere in the clause are left to a future structural parser.
    ``or related discipline`` and ``or its foreign equivalent`` are education
    alternatives that do not remove the explicitly additive experience.
    """
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("‘", "'")
    minima: list[int] = []
    clauses = re.split(r"[.;!?\r\n]+", text)
    for index, clause in enumerate(clauses):
        if _OPTIONAL.search(clause) or _ALTERNATIVE.search(clause):
            continue
        if index + 1 < len(clauses) and re.match(
            r"\s*(?:or|alternatively|instead)\b", clauses[index + 1], re.IGNORECASE
        ):
            continue
        # Academic qualifications are not evidence about the age of a company,
        # a team's collective history, or a named employee's biography.
        if re.search(
            r"\b(?:firm|company|business|team|organization)\s+"
            r"(?:has|have|brings?|offers?|celebrates?)\b"
            r"|\b(?:he|she|they)\s+(?:has|have|holds?|earned)\b",
            clause,
            re.IGNORECASE,
        ):
            continue
        matches = list(_ADDITIVE.finditer(clause))
        if len(matches) != 1:
            continue
        match = matches[0]
        # Only education-internal alternatives (subjects/foreign equivalence)
        # are safe. A later "or" may introduce any credential abbreviation,
        # even one interrupted by the sentence splitter, such as "M.Sc.".
        if re.search(r"\bor\b", clause[: match.start()], re.IGNORECASE) or re.search(
            r"\bor\b", clause[match.end() :], re.IGNORECASE
        ):
            continue
        # A second academic pathway makes a global minimum uncertain, even if
        # punctuation or a different connector separates the two pathways.
        if len(re.findall(_DEGREE, clause, flags=re.IGNORECASE)) != 1:
            continue
        if re.search(
            r"\b(?:experience|salary|compensation|bonus|age|history|founded|"
            r"employees?|staff|team|company|firm|business)\b",
            match["education"],
            re.IGNORECASE,
        ):
            continue
        low = int(match["low"])
        high = int(match["high"]) if match["high"] is not None else low
        if low <= high:
            minima.append(low)
    return list(dict.fromkeys(minima))
