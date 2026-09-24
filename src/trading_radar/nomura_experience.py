"""Conservative reading of Nomura's labelled experience requirements.

Only the audited Position Specifications table supplies typed provenance.
Other legacy Experience labels retain numeric recognition with ambiguity guards.
"""

import re

from trading_radar.models import ExperienceEvidence

NUMBER = re.compile(
    r"\bExperience\s*:?\s*(?P<low>[0-9]{1,2})(?:\s*[-–—]\s*(?P<high>[0-9]{1,2})|\s*\+)?\s*years?\b",
    re.IGNORECASE,
)
FIELD = re.compile(
    r"\b(?:Qualification(?:s)?|Corporate Title|Functional Title|Requisition No\.?|"
    r"R\s*ole\s*(?:&|and)\s*Responsibilities|Job Responsibilities|Mind Set|Skills\s*/\s*qualifications)\b",
    re.IGNORECASE,
)
AMBIGUOUS = re.compile(
    r"\b(?:preferred|preferable|desirable|desired|optional|advantage|ideally|"
    r"not|no|without|unnecessary|waived|or|either|degree|academic|university|"
    r"internship|company|firm|history)\b|\bnot\s+required\b",
    re.IGNORECASE,
)


def experience_minima(text: str) -> list[int]:
    """Keep labelled numeric minima, rejecting ambiguous duration requirements."""
    result = []
    for match in NUMBER.finditer(text):
        low, high = int(match["low"]), int(match["high"] or match["low"])
        if high < low:
            continue
        # Inspect the containing field/sentence, not unrelated qualifications.
        previous_fields = list(FIELD.finditer(text, 0, match.start()))
        start = previous_fields[-1].end() if previous_fields else 0
        for separator in (".", ";", "\n"):
            start = max(start, text.rfind(separator, start, match.start()) + 1)
        prefix = text[start : match.start()]
        next_field = FIELD.search(text, match.end())
        end = next_field.start() if next_field else len(text)
        for separator in (".", ";", "\n"):
            index = text.find(separator, match.end(), end)
            if index != -1:
                end = index
        suffix = text[match.end() : end]
        # The audited "preferably in <market>" qualifies the domain, not years.
        guarded_suffix = re.sub(r"\bpreferably\s+in\b", "in", suffix, flags=re.IGNORECASE)
        if (
            AMBIGUOUS.search(prefix)
            or AMBIGUOUS.search(guarded_suffix)
            or re.search(
                r"\bprefer(?:ably|red|ence)?\b", prefix + " " + guarded_suffix, re.IGNORECASE
            )
            or re.search(r"[\"“”]", prefix + suffix)
            or re.search(r"\b(?:less than|up to|at most|maximum)\b", prefix, re.IGNORECASE)
        ):
            continue
        result.append(low)
    return result


def nomura_experience_evidence(text: str) -> list[ExperienceEvidence]:
    """Attach the exact Experience field only in one unambiguous table."""
    headings = list(re.finditer(r"\bPosition Specifications\s*:?\s*", text, re.IGNORECASE))
    if len(headings) != 1:
        return []
    context_start = (
        max(text.rfind(".", 0, headings[0].start()), text.rfind("\n", 0, headings[0].start())) + 1
    )
    context = text[context_start : headings[0].start()]
    if re.search(
        r"\b(?:preferred|optional|not|required example|example)\b|[\"“”]", context, re.IGNORECASE
    ):
        return []
    start = headings[0].end()
    # Qualification terminates the Experience field in the audited template.
    end = re.search(r"\bQualifications?\b", text[start:], re.IGNORECASE)
    if not end or end.start() > 2000:
        return []
    block = text[start : start + end.start()]
    if not re.match(r"Corporate Title\b", block, re.IGNORECASE):
        return []
    fields = list(re.finditer(r"\bExperience\s*:?\s*(?=[0-9])", block, re.IGNORECASE))
    if len(fields) != 1:
        return []
    excerpt = block[fields[0].start() :].strip()
    # Deliberately bounded to the numeric field and two audited domain variants.
    # A preference for a market does not turn a required duration into a preference.
    value = re.fullmatch(
        NUMBER.pattern + r"(?:\s+of experience)?"
        r"(?:\s+(?:preferably\s+)?in Securitisation Market covering ABS/RMBS/CMBS"
        r"(?: in European or US markets)?)?\s*\.?",
        excerpt,
        re.IGNORECASE,
    )
    if not value:
        return []
    low, high = int(value["low"]), int(value["high"] or value["low"])
    prefix = block[: fields[0].start()]
    labels = [re.sub(r"\s+", " ", field[0]).casefold() for field in FIELD.finditer(prefix)]
    if labels != ["corporate title", "functional title"]:
        return []
    if high < low or AMBIGUOUS.search(prefix) or re.search(r"[\"“”]", prefix):
        return []
    return [
        ExperienceEvidence(
            minimum_years=low,
            kind="professional",
            origin="description",
            method="nomura_position_specifications",
            excerpt=excerpt,
        )
    ]
