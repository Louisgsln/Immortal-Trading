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
_WRITTEN_NUMBERS = {
    word: value
    for value, word in enumerate("zero one two three four five six seven eight nine ten".split())
}
_WRITTEN_ADDITIVE = re.compile(
    r"\b(?:requires?|must\s+have)\s+(?:an?\s+)?"
    + _DEGREE
    + r"(?P<education>[^.;!?\r\n]{0,180}?)\s+and\s+"
    r"(?P<word>zero|one|two|three|four|five|six|seven|eight|nine|ten)\s*"
    r"\((?P<low>\d{1,2})\)\s+years?\s+(?:of\s+)?"
    r"(?:(?:relevant|progressive|professional|related|technical|work|working)\s+){0,3}experience\b",
    re.IGNORECASE,
)
_WRITTEN_SECTION = re.compile(
    r"\b(?P<optional>(?:preferred|recommended|optional|desirable)\s+(?:qualifications|requirements|skills)|nice\s+to\s+have)\b"
    r"|\b(?P<required>(?:(?:required|minimum|basic|essential)\s+)?qualifications|requirements|your\s+skills\s+and\s+experience)\b",
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
    """Read explicit degree-plus clauses and required degree-and-written-number clauses.

    Bound the degree-to-plus gap and experience modifiers. Sentence, semicolon
    and line boundaries are never crossed. Ambiguous education alternatives or
    preferences anywhere in the clause are left to a future structural parser.
    ``or related discipline`` and ``or its foreign equivalent`` are education
    alternatives that do not remove the explicitly additive experience.
    """
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("‘", "'")
    minima: list[int] = []
    spans = list(re.finditer(r"[^.;!?\r\n]+", text))
    clauses = [span[0] for span in spans]
    sections = list(_WRITTEN_SECTION.finditer(text))
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
        matches = list(_ADDITIVE.finditer(clause)) + list(_WRITTEN_ADDITIVE.finditer(clause))
        if len(matches) != 1:
            continue
        match = matches[0]
        if match.re is _WRITTEN_ADDITIVE:
            position = spans[index].start() + match.start()
            section = next((s for s in reversed(sections) if s.end() <= position), None)
            if section is not None and section.lastgroup == "optional":
                continue
            if _WRITTEN_NUMBERS[match["word"].lower()] != int(match["low"]):
                continue
            if re.search(
                r"\b(?:not|without|no|never|up\s+to|maximum|at\s+most|less\s+than|preferred|optional)\b",
                clause,
                re.IGNORECASE,
            ):
                continue
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
        high = int(match["high"]) if match.groupdict().get("high") is not None else low
        if low <= high:
            minima.append(low)
    return list(dict.fromkeys(minima))
