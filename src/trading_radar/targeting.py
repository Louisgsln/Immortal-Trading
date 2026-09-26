"""Narrow role evidence from audited employer descriptions, not firm boilerplate."""

import html
import re

from trading_radar.description_sections import labelled_lists, visible_text
from trading_radar.finance_sections import EMPLOYERS, RESPONSIBILITIES
from trading_radar.html_page import Document, Element
from trading_radar.models import Job
from trading_radar.normalizer import has, normalize_text

OPERATIONAL_EXCLUSION = "Missions vérifiées de support opérationnel, hors cible trading"
_OPERATIONAL_ASSISTANTS = {
    ("ubs_professionals", "ubs", "trader assistant"): (
        "key responsibilities",
        "your career comeback",
        (
            "provide operations support to the trading desk",
            "trade bookings",
            "ensure data integrity",
        ),
    ),
    ("bnp_paribas", "bnp paribas", "institutional sales trading assistant"): (
        "your main activities are",
        "profile and skills to success",
        ("finalise their onboarding", "finalising booking of traded deals", "pre trade checks"),
    ),
    ("morgan_stanley", "morgan stanley", "investment management trading assistant analyst"): (
        "primary responsibilities",
        "qualifications external",
        ("perform post trade functions", "ensure settlement of trades", "confirm and clear"),
    ),
    ("morgan_stanley", "morgan stanley", "asia rates trading assistant"): (
        "primary responsibilities",
        "educational background",
        ("trade bookings and amendments", "end of day p and l reviews", "lifecycle management"),
    ),
    ("morgan_stanley", "morgan stanley", "msim emerging markets trading assistant analyst"): (
        "key responsibilities",
        "candidate profile",
        (
            "settlement and reconciliation",
            "account maintenance and onboarding",
            "resolve trading and settlement issues",
        ),
    ),
}


def operational_role(job: Job) -> bool:
    """Reviewed operational duties, not all assistant/support job titles."""
    rule = _OPERATIONAL_ASSISTANTS.get((job.source, job.company_normalized, job.title_normalized))
    if job.source_type != "official" or rule is None:
        return False
    start, end, requirements = rule
    section = _section(
        normalize_text(visible_text(Document(html.unescape(job.description)).root)), start, end
    )
    return all(has(section, phrase) for phrase in requirements)


def nomura_trading_technology(job: Job) -> bool:
    if (job.source_type, job.source, job.company_normalized, job.title_normalized) != (
        "official",
        "nomura_professionals",
        "nomura",
        "trading support",
    ):
        return False
    section = _section(
        normalize_text(visible_text(Document(html.unescape(job.description)).root)),
        "r ole and responsibilities",
        "we are committed to providing equal opportunities",
    )
    return all(
        has(section, term)
        for term in (
            "quants to work on our algorithmic trading platform for efx",
            "talented programmers",
            "guiding models through the entire development lifecycle",
            "develop and manage quantitative analytics",
        )
    )


def _section(text: str, start: str, end: str) -> str:
    if text.count(start) != 1:
        return ""
    rest = text.split(start)[1]
    return rest.split(end)[0] if rest.count(end) == 1 else ""


def research_trading_evidence(job: Job) -> bool:
    if job.source_type != "official":
        return False
    text = normalize_text(job.description_text.replace("’", "'"))
    title = job.title_normalized
    if job.company_normalized == EMPLOYERS.get(job.source) and any(
        has(title, term) for term in ["quantitative researcher", "quant researcher"]
    ):
        sections = list(
            labelled_lists(
                Document(html.unescape(job.description)).root, RESPONSIBILITIES[job.source]
            )
        )
        if len(sections) != 1:
            return False
        for item in sections[0][1].children:
            if not isinstance(item, Element) or item.tag != "li":
                continue
            duty = normalize_text(visible_text(item))
            if (
                has(duty, "trading")
                and re.search(r"\b(?:develop|build|design|implement|research)\w*\b", duty)
                and any(
                    has(duty, term)
                    for term in [
                        "trading strategies",
                        "trading signals",
                        "pricing models",
                        "predictive models",
                    ]
                )
            ):
                return True
        return False
    if (
        job.source == "jane_street"
        and job.company_normalized == "jane street"
        and title == "quantitative researcher"
    ):
        role = _section(text, "about the position", "about you")
        return all(
            term in role
            for term in [
                "build models strategies and systems that price and trade financial instruments",
                "run trading strategies",
            ]
        )
    if (
        job.source == "drw"
        and job.company_normalized == "drw"
        and title == "quant researcher compute markets"
    ):
        role = _section(text, "what you would do", "what we are looking for")
        return all(
            term in role
            for term in [
                "build and own the pricing framework",
                "produce reservation bids and offers",
                "work directly with trading risk",
            ]
        )
    if (
        job.source == "jump_trading"
        and job.company_normalized == "jump trading"
        and title == "quantamental research analyst trading team"
    ):
        role = _section(text, "what you ll do", "skills you ll need")
        return all(
            term in role
            for term in [
                "collaborate with quantitative traders",
                "etf pricing and trading strategy",
                "determine fair value and generate trade ideas",
            ]
        )
    return False


def drw_junior_role(job: Job) -> bool:
    if (job.source_type, job.source, job.company_normalized, job.title_normalized) != (
        "official",
        "drw",
        "drw",
        "trader",
    ):
        return False
    text = normalize_text(job.description_text.replace("’", "'"))
    intro = _section(text, "as a junior trader you will", "responsibilities")
    duties = _section(text, "responsibilities", "required experience")
    return (
        "operate trading strategies" in intro
        and "manually trade to reduce risk exposure when necessary" in duties
        and "adjust system parameters dynamically based on market conditions" in duties
    )
