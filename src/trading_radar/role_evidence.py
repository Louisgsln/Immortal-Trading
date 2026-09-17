"""Remove only audited corporate asset descriptions from role evidence."""

import re

from trading_radar.models import Job

# These two complete passages were checked against the official DRW capture
# and all 27 stored DRW descriptions. Unknown wording must remain intact.
_DRW_CORPORATE_PASSAGES = (
    "Headquartered in Chicago with offices throughout the U.S., Canada, Europe, and Asia, "
    "we trade a variety of asset classes including Fixed Income, ETFs, Equities, FX, "
    "Commodities and Energy across all major global markets. We have also leveraged "
    "our expertise and technology to expand into three non-traditional strategies: "
    "real estate, venture capital and cryptoassets.",
    "DRW is a major Chicago-based proprietary trading firm founded in 1992 by Don Wilson, "
    "specializing in diversified, technology-driven market-making and quantitative trading "
    "across asset classes including fixed income, options, derivatives, commodities, "
    "energy, equities, FX, and cryptocurrency.",
)
_DRW_CORPORATE_PATTERNS = tuple(
    re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, passage.split())) + r"(?!\w)")
    for passage in _DRW_CORPORATE_PASSAGES
)


def role_evidence_text(job: Job) -> str:
    """Return stored description text minus exact verified DRW corporate spans.

    This is a view for asset/profile evidence only. It must not replace the
    original description or the text used for eligibility and exclusions.
    Match wording and punctuation exactly, tolerating whitespace layout only.
    Preserve all other characters, including role duties following the company
    introduction; never rebuild the text from HTML or remove an About section.
    """
    text = job.description_text
    if (
        job.company.strip().casefold() != "drw"
        or job.company_normalized != "drw"
        or job.source != "drw"
        or job.source_type != "official"
    ):
        return text
    for pattern in _DRW_CORPORATE_PATTERNS:
        text = pattern.sub("", text)
    return text
