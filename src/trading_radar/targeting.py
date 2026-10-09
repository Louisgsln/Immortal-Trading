"""Narrow role evidence from audited employer descriptions, not firm boilerplate."""

import html
import re

from trading_radar.description_sections import labelled_lists, visible_text
from trading_radar.finance_sections import EMPLOYERS, RESPONSIBILITIES
from trading_radar.html_page import Document, Element
from trading_radar.models import Job
from trading_radar.normalizer import has, normalize_text

OPERATIONAL_EXCLUSION = "Missions vérifiées de support opérationnel, hors cible trading"


def sg_desk_title(title: str) -> bool:
    return bool(re.fullmatch(r"(?:(?:vie|v i e) )?(?:one delta|delta one) desk analyst", title))


def sg_desk_technology(job: Job) -> bool:
    """SG's collector verified the actual duty bullets before storing this hint."""
    return (
        (job.source_type, job.source, job.company_normalized)
        == ("official", "societe_generale", "societe generale")
        and sg_desk_title(job.title_normalized)
        and job.role_hint == "trading_technology"
    )


def tp_broking_duties(job: Job) -> str:
    """Audited trainee broking duties, including execution/quotes beyond support."""
    if (job.source_type, job.source, job.company_normalized) != (
        "official",
        "tp_icap",
        "tp icap",
    ) or not re.fullmatch(r"trainee broker(?: .+)?", job.title_normalized):
        return ""
    sections = list(
        labelled_lists(
            Document(html.unescape(job.description)).root,
            {"role responsibilities", "responsibilities"},
        )
    )
    if len(sections) != 1:
        return ""
    duties = visible_text(sections[0][1])
    items = [
        normalize_text(visible_text(item))
        for item in sections[0][1].children
        if isinstance(item, Element) and item.tag == "li"
    ]

    def stated(term: str) -> bool:
        return any(item == term or item.startswith(term + " ") for item in items)

    quoted = all(
        stated(term)
        for term in (
            "identify trade opportunities and calculate strategies",
            "give live quotes to traders",
            "liaise with clients",
        )
    )
    execution = all(
        stated(term)
        for term in (
            "arrange or introduce trades from client orders",
            "develop existing and new client relationships",
            "understand the underlying products being traded by clients",
        )
    )
    return duties if quoted or execution else ""


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


_FINANCE_ROLES = {
    ("tp_icap", "algorithmic trading developer"): (
        "technology",
        "role responsibilities",
        "experience competences",
        (
            "work closely with quants on implementation of trading algorithms",
            "quantitative models and analytical signals",
            "low latency trading strategies",
        ),
    ),
    ("squarepoint_capital", "junior quant researcher"): (
        "research",
        "position overview",
        "required qualifications",
        (
            "research and implement strategies within the firm s automated trading framework",
            "identify trading opportunities",
            "researching and implementing trading ideas",
        ),
    ),
    ("squarepoint_capital", "junior quant researcher ml alpha research"): (
        "research",
        "position overview",
        "required qualifications",
        (
            "identify trading opportunities",
            "researching new statistical and ml techniques",
            "deploy and monitor models used to generate trading signals",
        ),
    ),
    ("squarepoint_capital", "junior quant developer"): (
        "technology",
        "position overview",
        "required qualifications",
        (
            "implement novel trading strategies",
            "identify new trading opportunities",
            "backtesting simulations",
        ),
    ),
    ("squarepoint_capital", "graduate quant developer"): (
        "technology",
        "role and responsibilities",
        "required qualifications",
        (
            "software engineering skills to support investment research and trading",
            "work closely with quantitative researchers",
            "workflows for alpha generation",
            "frameworks used by researchers and traders globally",
        ),
    ),
    ("chicago_trading_campus", "systematic quantitative researcher phd"): (
        "research",
        "the role",
        "qualifications phd in science or engineering fields",
        (
            "trading strategy generation",
            "back testing",
            "statistical analysis",
            "build predictive and explanatory models",
            "trading infrastructure",
        ),
    ),
    ("dv_trading", "quantitative researcher"): (
        "research",
        "responsibilities",
        "requirements",
        (
            "develop and refine signals grounded in market microstructure analysis",
            "collaborate with traders to translate research into deployable strategies",
            "signal research backtesting and production deployment",
        ),
    ),
}


def finance_role_evidence(job: Job, role: str) -> bool:
    """Audited exact roles; general employer language cannot supply missing duties."""
    rule = _FINANCE_ROLES.get((job.source, job.title_normalized))
    if (
        job.source_type != "official"
        or rule is None
        or rule[0] != role
        or job.company_normalized != EMPLOYERS.get(job.source)
    ):
        return False
    text = normalize_text(
        visible_text(Document(html.unescape(job.description)).root).replace("’", "'")
    )
    section = _section(text, rule[1], rule[2])
    return all(has(section, phrase) for phrase in rule[3])


def research_trading_evidence(job: Job) -> bool:
    if job.source_type != "official":
        return False
    if (job.source, job.company_normalized) == (
        "morgan_stanley_campus",
        "morgan stanley",
    ) and re.fullmatch(
        r"20\d{2} quantitative finance off cycle internship(?: .+)?", job.title_normalized
    ):
        nodes = list(Document(html.unescape(job.description)).root.walk())
        starts = [
            i
            for i, node in enumerate(nodes)
            if node.tag == "strong"
            and normalize_text(visible_text(node)) == "roles and responsibilities"
        ]
        ends = [
            i
            for i, node in enumerate(nodes)
            if node.tag == "strong"
            and normalize_text(visible_text(node)) == "qualifications skills requirements"
        ]
        if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
            return False
        # Oleeo nests headings in paragraphs with line breaks; use their bounded
        # DOM section, never firm boilerplate or candidate qualifications.
        lists = [node for node in nodes[starts[0] + 1 : ends[0]] if node.tag == "ul"]
        return len(lists) == 1 and any(
            isinstance(item, Element)
            and item.tag == "li"
            and all(
                has(normalize_text(visible_text(item)), phrase)
                for phrase in ("pricing models", "hedging", "trading decisions")
            )
            for item in lists[0].children
        )
    if finance_role_evidence(job, "research"):
        return True
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
