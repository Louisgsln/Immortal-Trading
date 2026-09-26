"""Narrow role evidence from audited employer descriptions, not firm boilerplate."""

from trading_radar.models import Job
from trading_radar.normalizer import normalize_text


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
