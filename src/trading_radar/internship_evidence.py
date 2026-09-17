"""Recognize audited Jane Street descriptions of the recipient's internship."""

import re
import unicodedata

from trading_radar.models import Job

INTERNSHIP_EXCLUSION = "description explicitly identifies a Jane Street internship"

_RECIPIENT = re.compile(
    r"(?:as\s+an?\s+(?:[a-z]+\s+){0,5}intern\s*,\s*"
    r"you(?:'ll\s+|\s+(?:are|will)\s+)"
    r"|(?:during\s+the|over\s+the\s+course\s+of\s+your)\s+internship\s*,?\s*(?:"
    r"you(?:'ll\s+|\s+(?:are|will)\s+)|your\s+work\s+is\s+)"
    r"|you(?:'ll|\s+will)\s+spend\s+the\s+bulk\s+of\s+your\s+internship\b)",
    re.IGNORECASE,
)
_UNSAFE_CONTEXT = re.compile(
    r"\b(?:if|unless|would|could|might|not|never|former|formerly|previous|previously|"
    r"past|historical|historically|once|used\s+to|no\s+longer|last\s+(?:year|summer))\b"
    r"|\b(?:you(?:'ll|\s+will)?\s+(?:mentor|supervise|recruit|hire)|"
    r"as\s+(?:an?\s+)?(?:mentor|supervisor|recruiter))\b",
    re.IGNORECASE,
)
_QUOTE = re.compile(r'"[^"\r\n]*"|“[^”]*”|«[^»]*»|‘[^’]*’|(?<!\w)\'[^\r\n]*?\'(?!\w)')


def explicit_jane_street_internship(job: Job) -> bool:
    """Find an affirmative, current/future internship addressed to the candidate.

    This only applies to the audited official Jane Street source. It supplies
    exclusion evidence; it must not rewrite the contract, title or description.
    Accept only sentence starts (or the flattened About the Position heading).
    Quotes, conditional/past examples and responsibility for other interns are
    deliberately outside this narrow rule.
    """
    if (
        job.source != "jane_street"
        or job.source_type != "official"
        or job.company_normalized != "jane street"
    ):
        return False
    text = unicodedata.normalize("NFKC", job.description_text)
    # Remove complete quoted spans before splitting sentences: a quote can
    # contain a period and must not turn its next sentence into fresh evidence.
    text = _QUOTE.sub(lambda match: " " * len(match[0]), text)
    text = text.replace("’", "'")
    for sentence in re.split(r"[.;!?\r\n]+", text):
        sentence = re.sub(r"^\s*About\s+the\s+Position\s*:?\s*", "", sentence, flags=re.I)
        sentence = sentence.strip()
        if _RECIPIENT.match(sentence) and not _UNSAFE_CONTEXT.search(sentence):
            return True
    return False
