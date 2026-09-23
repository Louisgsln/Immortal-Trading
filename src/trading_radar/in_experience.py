"""Read bounded professional qualifications phrased as ``N+ years in ...``."""

import re
import unicodedata

_YEARS_IN = re.compile(
    r"(?<![\w.+\-–—])(?P<low>\d{1,2})"
    r"(?:[ \t]*[-–—][ \t]*(?P<high>\d{1,2})|[ \t]*\+)"
    r"[ \t]+years?[ \t]+in[ \t]+",
    re.IGNORECASE,
)
# Initial vocabulary comes from individually audited professional activities.
# A qualification section alone cannot turn any arbitrary duration into work.
_DOMAIN = re.compile(
    r"(?:buy/sell-side\s+research|prop\s+trading|ETF/index\s+research|"
    r"corporate\s+actions\s+analysis|site\s+reliability|systems\s+engineering|"
    r"technical\s+operations|FPGA|(?:low-latency\s+)?C\+\+\s+development|"
    r"options\s+trading|market\s+making|floor\s+brokerage|exchange\s+operations|"
    r"Risk\s*(?:&|and)\s*Controls\s+roles|"
    r"(?:the\s+)?Financial\s+Services\s*/\s*Banking\s+industry)(?!\w)",
    re.IGNORECASE,
)
_SECTION = re.compile(
    r"\b(?P<optional>(?:recommended|preferred|desirable|optional)\s*"
    r"(?::|(?:qualifications|requirements|skills)\b)|nice\s+to\s+have\b)"
    r"|\b(?P<other>about\s+(?:us|the\s+(?:company|firm))|our\s+(?:company|history)|"
    r"(?:key\s+)?responsibilities|what\s+you(?:'ll|\s+will)\s+get|benefits)\b"
    r"|\b(?P<required>(?:(?:basic|minimum|required|essential)\s+)?qualifications|"
    r"requirements|about\s+you|who\s+you\s+are|your\s+skills\s+(?:and|&)\s+experience|"
    r"skills\s+you(?:'ll|\s+will)\s+need|what\s+you\s+bring|"
    r"what\s+we(?:'re|\s+are)\s+looking\s+for)\b",
    re.IGNORECASE,
)
_OPTIONAL = re.compile(
    r"\b(?:preferred|preferable|preferably|recommended|desirable|desired|ideally|ideal|"
    r"typically|usually|approximately|roughly|around|optional|advantageous|"
    r"nice\s+to\s+have|a\s+plus|an?\s+(?:advantage|asset)|"
    r"not\s+(?:required|needed|essential|necessary|mandatory|a\s+must))\b",
    re.IGNORECASE,
)
_NOT_MINIMUM = re.compile(
    r"\b(?:up\s+to|less\s+than|at\s+most|no\s+more\s+than|maximum(?:\s+of)?|"
    r"without|need\s+not|must\s+not|do(?:es)?\s+not\s+(?:need|require)|"
    r"don't\s+need|no\s+(?:need|requirement)\s+for|not\s+necessary\s+to\s+have|"
    r"contract|placement|extension|duration|tenure|founded|established|"
    r"(?:our|the|this)\s+(?:company|firm|team|organization)|"
    r"(?:we|he|she|they)\s+(?:have|has|bring|brings)|"
    r"will\s+(?:spend|work|serve))\b",
    re.IGNORECASE,
)
_ALTERNATIVE = re.compile(
    r"\b(?:either|alternatively|instead|in\s+lieu|substitut\w*|waiv\w*)\b"
    r"|\bor\s+(?:(?:an?|the)\s+)?(?:\d|(?:no|zero)\s+experience|"
    r"equivalent\s+(?:work\s+)?experience|"
    r"(?:bachelor|master|doctoral|doctorate|phd|degree|bsc|msc|bs|ms|mba|jd)\b)",
    re.IGNORECASE,
)
_BOUNDARY = re.compile(r"[.;!?\r\n•]+")
_NEXT_ITEM = re.compile(
    r"\s+(?=(?:Strong|Excellent|Demonstrated|Knowledge|Ability|High|Have|Good|"
    r"Comfortable|Desire|Solid|Proficiency|Familiarity|Hands-on|Bachelor|Master|"
    r"A\s+software-development)\b)"
)
_DOMAIN_PREFERENCE = re.compile(
    r",\s*ideally\s+supporting\s+(?:high-performance(?:\s+or\s+real-time)?|real-time)"
    r"\s+systems\b",
    re.IGNORECASE,
)


def candidate_in_experience_years(text: str) -> list[int]:
    """Return lower bounds for audited activities in required candidate sections.

    Plain ``N years`` and ``track record`` are deliberately outside this rule.
    Preserve section state across ATS-flattened bullets, but do not apply later
    preferred sections retroactively. The audited ``ideally supporting ...
    systems`` clause qualifies a domain, not the preceding number of years.
    """
    text = unicodedata.normalize("NFKC", text).replace("’", "'")
    sections = list(_SECTION.finditer(text))
    minima: list[int] = []
    for match in _YEARS_IN.finditer(text):
        low = int(match["low"])
        if match["high"] is not None and low > int(match["high"]):
            continue
        domain = _DOMAIN.match(text, match.end())
        if domain is None:
            continue
        preceding = [s for s in sections if s.end() <= match.start()]
        if not preceding or preceding[-1].lastgroup != "required":
            continue
        section = preceding[-1]
        boundaries = list(_BOUNDARY.finditer(text, section.end(), match.start()))
        start = boundaries[-1].end() if boundaries else section.end()
        ending = _BOUNDARY.search(text, domain.end())
        stop = ending.start() if ending else len(text)
        next_section = next((s for s in sections if s.start() >= domain.end()), None)
        if next_section:
            stop = min(stop, next_section.start())
        after = text[domain.end() : stop]
        next_item = _NEXT_ITEM.search(after)
        if next_item and not re.search(
            r"\bor\s+(?:an?\s+)?$", after[: next_item.end()], re.IGNORECASE
        ):
            after = after[: next_item.start()]
        before = text[start : match.start()]
        clause = before + text[match.start() : domain.end()] + after
        if _ALTERNATIVE.search(clause) or re.match(
            r"\s*(?:[.;\r\n]+\s*)?(?:or|alternatively|instead)\b", text[stop:], re.IGNORECASE
        ):
            continue
        if re.search(r"\bor\s*$", text[section.end() : match.start()], re.IGNORECASE):
            continue
        if _NOT_MINIMUM.search(clause) or _OPTIONAL.search(before):
            continue
        if _OPTIONAL.search(_DOMAIN_PREFERENCE.sub("", after)):
            continue
        minima.append(low)
    return list(dict.fromkeys(minima))
