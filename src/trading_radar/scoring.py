import html
import re

from trading_radar.degree_experience import degree_experience_years
from trading_radar.in_experience import candidate_in_experience_years
from trading_radar.internship_evidence import INTERNSHIP_EXCLUSION, explicit_jane_street_internship
from trading_radar.models import Job, Score
from trading_radar.normalizer import has, normalize_text
from trading_radar.range_experience import plain_range_experience_years
from trading_radar.role_evidence import role_evidence_text
from trading_radar.targeting import drw_junior_role, research_trading_evidence

ROLE_TERMS = {
    "TRADING": ["trader", "trading"],
    "QUANT_TRADING": [
        "quant trader",
        "quantitative trader",
        "quantitative trading",
        "algorithmic trading",
        "systematic trading",
    ],
    "MARKET_MAKING": ["market making", "market maker"],
    "ELECTRONIC_TRADING": ["electronic trading", "etrading", "efx"],
    "SALES_TRADING": ["sales and trading"],
    "STRUCTURING": ["structuring", "structurer", "structuration"],
    "REPO": ["repo"],
    "SECURITIES_FINANCE": ["securities finance", "securities lending", "prime finance"],
    "TRADING_TECH": [
        "trading technology",
        "trading systems",
        "trading developer",
        "front office developer",
    ],
}
ASSET_TERMS = {
    "FX": ["fx", "foreign exchange", "ndf", "efx"],
    "RATES": ["rates", "government bonds", "irs", "ois", "inflation", "stir", "money markets"],
    "CREDIT": ["credit", "cds", "high yield", "investment grade"],
    "EQUITIES": ["equities", "equity", "stocks"],
    "COMMODITIES": ["commodities", "commodity", "energy", "metals", "agriculture"],
    "OPTIONS": ["options", "option"],
    "VOLATILITY": ["volatility"],
    "DELTA_ONE": ["delta one"],
    "REPO": ["repo"],
    "SECURITIES_FINANCE": ["securities finance", "securities lending", "prime finance"],
    "MACRO": ["macro"],
    "CRYPTO": ["crypto", "digital assets"],
    "CROSS_ASSET": ["cross asset", "multi asset", "derivatives"],
}

ASSOCIATE_EXCLUSION = "Poste Associate sans ouverture explicite au niveau Analyst"
_ANALYST_ASSOCIATE = re.compile(
    r"\b(?:analysts?\s*(?:[/&|]|and|or)\s*associates?|"
    r"associates?\s*(?:[/&|]|and|or)\s*analysts?)\b",
    re.IGNORECASE,
)


def associate_only(job: Job) -> bool:
    """Owner's target excludes Associate unless the title offers Analyst as well.

    This is a targeting preference, not an inferred number of years or a claim
    that Associate has the same meaning at every employer. Body text and junior
    hints cannot override the advertised grade.
    """
    return any(has(job.title_normalized, grade) for grade in ("associate", "associates")) and not (
        _ANALYST_ASSOCIATE.search(html.unescape(job.title))
    )


def classify(text: str, rules: dict[str, list[str]]) -> list[str]:
    return [label for label, terms in rules.items() if any(has(text, t) for t in terms)]


def required_experience_years(text: str) -> list[int]:
    """Read numeric requirements and range minima, excluding attached preferences."""
    # Academic alternatives need the original punctuation and range endpoints.
    additive_minima = degree_experience_years(text)
    range_minima = plain_range_experience_years(text)
    in_minima = candidate_in_experience_years(text)

    def lower_bound(match: re.Match[str]) -> str:
        low, high, plus, years = match.groups()
        if int(low) > int(high):
            return " ambiguous experience range "
        return f"{low}{plus or ''} {years}"

    # The search normalizer otherwise erases the dash, causing the upper number
    # of `2-5+ years` to be misread as a separate minimum of five years.
    text = re.sub(
        r"(?<!\d)(\d+)\s*[-–—]\s*(\d+)(\s*\+)?\s*(years?)\b",
        lower_bound,
        text,
        flags=re.IGNORECASE,
    )
    patterns = [
        r"(?:minimum(?: of)?|at least|requires?|required|must have)\s+(\d+)\s*\+?\s*years?",
        r"(\d+)\s*\+?\s*years?\s+(?:of\s+)?(?:relevant\s+)?experience\s+(?:is\s+)?required",
        r"\b(\d+)\s*\+\s*years?\s+(?:of\s+)?(?:\w+\s+){0,3}experience\b",
    ]
    minima = []
    # Keep the existing global search text. A parallel string with identical
    # offsets retains punctuation only for the scope of optional qualifiers.
    search_parts: list[str] = []
    context_parts: list[str] = []
    separator = " "
    for position, part in enumerate(re.split(r"([.;!?\n\r,]+)", text)):
        if position % 2:
            if re.search(r"[.;!?\n\r]", part):
                separator = "."
            elif separator != ".":
                separator = ","
        elif normalized := normalize_text(part):
            if search_parts:
                context_parts.append(separator)
            search_parts.append(normalized)
            context_parts.append(normalized)
            separator = " "
    text = " ".join(search_parts)
    context = "".join(context_parts)
    for index, pattern in enumerate(patterns):
        for match in re.finditer(pattern, text):
            start = context.rfind(".", 0, match.start()) + 1
            stop = context.find(".", match.end())
            before = context[start : match.start()]
            after = context[match.end() : stop if stop != -1 else len(context)]
            if index == 0:
                # This pattern stops at "years"; extend only through an adjacent
                # experience phrase before checking its optional qualifier.
                experience = re.match(
                    r"\s+(?:of\s+)?(?:(?!and\b|or\b|but\b)\w+\s+){0,3}experience\b",
                    after,
                )
                if experience:
                    after = after[experience.end() :]
            # Only qualifiers attached directly to this experience statement:
            # "7+ years experience, preferably in futures" still requires seven.
            optional = "." not in context[match.start() : match.end()] and (
                re.search(
                    r"\b(?:preferred(?: qualifications)?|preferably|ideally|nice to have|"
                    r"experience desirable)\s*"
                    r"(?:,\s*)?(?:(?:minimum(?: of)?|at least|requires?|required|must have)\s+)?$",
                    before,
                )
                or re.match(
                    r"(?:\s+|,\s*)(?:is\s+)?(?:preferred|desirable|advantageous|a plus|optional|not required|not essential)\b",
                    after,
                )
            )
            business = re.search(
                r"\b(?:our|the|this)\s+(?:firm|company|business|team|organization)"
                r"\s+(?:has|have|brings?|offers?|with)\s*(?:at least\s*)?$",
                text[: match.start()],
            )
            if not optional and not business:
                minima.append(int(match[1]))
    return list(dict.fromkeys([*minima, *additive_minima, *range_minima, *in_minima]))


def score_job(job: Job, keywords: dict[str, list[str]]) -> Job:
    title = job.title_normalized
    text = normalize_text(job.title + " " + job.description_text)
    evidence_description = role_evidence_text(job)
    evidence_text = normalize_text(job.title + " " + evidence_description)
    result = Score()
    roles = classify(title, ROLE_TERMS)
    verified_research = research_trading_evidence(job)
    if verified_research:
        roles = list(dict.fromkeys([*roles, "QUANT_RESEARCH"]))
        result.reasons.append(
            "Audited role duties link quantitative research to pricing and trading decisions"
        )
    assets = classify(evidence_text, ASSET_TERMS)
    if evidence_description != job.description_text:
        result.reasons.append(
            "Asset and profile evidence excludes a verified DRW company paragraph"
        )
    junior = (
        job.seniority_hint == "junior"
        or drw_junior_role(job)
        or any(
            has(title, t)
            for t in [
                "graduate",
                "new grad",
                "analyst",
                "junior",
                "early careers",
                "entry level",
                "vie",
                "v i e",
            ]
        )
    )
    result.exclusions = [t for t in keywords["excluded_titles"] if has(title, t)]
    if verified_research and "research analyst" in result.exclusions:
        result.exclusions.remove("research analyst")
    excluded_associate = associate_only(job)
    if excluded_associate:
        result.exclusions.append(ASSOCIATE_EXCLUSION)
    contract = normalize_text(job.employment_type or "")
    if any(
        has(contract, t)
        for t in ["internship", "intern", "stage", "apprenticeship", "apprentice", "alternance"]
    ):
        result.exclusions.append("internship or apprenticeship contract")
    if explicit_jane_street_internship(job):
        result.exclusions.append(INTERNSHIP_EXCLUSION)
    # Senior titles override 'Analyst' when both occur (e.g. VP / Trading Analyst).
    result.exclusions += [t for t in keywords["senior_titles"] if has(title, t)]
    if job.seniority_hint == "senior":
        result.exclusions.append("employer explicitly classifies the role as senior")
    if has(title, "senior") and not has(title, "junior"):
        result.exclusions.append("senior title")
    if has(title, "sales") and not roles:
        result.exclusions.append("pure sales")
    tech = any(
        has(title, t) for t in ["software", "developer", "engineer", "technology", "systems"]
    )
    if tech:
        verified_technology = job.role_hint == "trading_technology"
        embedded = (
            verified_technology
            or bool(roles)
            and any(
                has(text, t)
                for t in ["front office", "trading desk", "electronic trading", "market making"]
            )
        )
        if embedded:
            roles = list(dict.fromkeys([*roles, "TRADING_TECH"]))
            if verified_technology:
                result.reasons.append(
                    "Employer department and role description confirm trading technology"
                )
        else:
            result.exclusions.append("software role without embedded trading evidence")
    job.desk = roles or ["NON_TRADING"]
    job.asset_class = assets or ["UNKNOWN"]
    job.seniority = (
        "senior"
        if job.seniority_hint == "senior" or any(has(title, t) for t in keywords["senior_titles"])
        else "associate"
        if excluded_associate
        else "junior"
        if junior
        else "unknown"
    )
    job.programme_type = (
        "graduate"
        if has(title, "graduate")
        else "VIE"
        if has(title, "vie") or has(title, "v i e")
        else None
    )
    if any(
        r in roles
        for r in [
            "TRADING",
            "QUANT_TRADING",
            "MARKET_MAKING",
            "ELECTRONIC_TRADING",
            "SALES_TRADING",
        ]
    ):
        result.trading = 30
    elif roles:
        result.trading = 22
    elif has(title, "global markets") or has(title, "markets analyst"):
        result.trading = 18
    if "TRADING_TECH" in roles:
        result.trading = min(result.trading, 22)
    result.junior = 0 if excluded_associate else 20 if junior else 5
    required = required_experience_years(job.description_text)
    if job.minimum_experience_years is not None:
        required.append(job.minimum_experience_years)
    if re.search(r"(?:hire|hiring|seeking|recruiting)\s+(?:an?\s+)?experienced\b", text):
        result.junior = 0
        result.reasons.append("Employer explicitly seeks an experienced hire")
    if required and max(required) > 2:
        result.junior = 0
        result.reasons.append("Explicit experience requirement exceeds 2 years")
        if max(required) >= 5:
            result.exclusions.append("requires at least 5 years of experience")
    # A year in unrelated boilerplate must not imply an intake date.
    start_text = normalize_text(job.expected_start_date or "")
    start_context = " ".join(
        re.findall(r"(?:start|intake|joining|commencing|programme|program)\b.{0,45}", text)
    )
    start_context += " " + " ".join(
        re.findall(r"\b20\d{2}\s+(?:graduate\s+)?(?:intake|programme|program|start)\b", text)
    )
    evidence = " ".join([title, start_text, start_context])
    result.start = (
        15
        if has(evidence, "2027")
        else 11
        if has(evidence, "2026")
        else 4
        if has(evidence, "2028")
        else 7
    )
    if has(evidence, "flexible"):
        result.start = max(result.start, 11)
    title_years = set(re.findall(r"\b202[6-8]\b", title))
    stated_years = set(re.findall(r"\b202[6-8]\b", start_text + " " + start_context))
    if title_years and stated_years and stated_years - title_years:
        result.start = 7
        result.reasons.append(
            "Conflicting intake years in title and description; verify start date"
        )
    direct = result.trading >= 25
    fo = (
        verified_research
        or (tech and job.role_hint == "trading_technology")
        or any(
            has(text, t)
            for t in [
                "front office",
                "trading desk",
                "market making",
                "liquidity provision",
                "sales and trading",
                "electronic trading",
                "global markets",
            ]
        )
    )
    result.front_office = 15 if direct or (result.trading > 0 and fo) else 0
    result.asset = 10 if assets else 0
    result.matched_keywords = [t for t in keywords["profile_terms"] if has(evidence_text, t)]
    result.profile_fit = min(10, len(result.matched_keywords) * 2)
    if not result.trading:
        result.junior = result.start = result.asset = result.profile_fit = 0
    result.reasons += [
        f"{'Role' if job.role_hint else 'Title'} classification: {', '.join(job.desk)} ({result.trading}/30)",
        f"Junior compatibility: {result.junior}/20",
        f"Start: {result.start}/15"
        + ("; date unknown" if result.start == 7 else "; explicit date evidence"),
        f"Front Office evidence: {result.front_office}/15",
        f"Assets: {', '.join(job.asset_class)} ({result.asset}/10)",
        f"Profile terms: {', '.join(result.matched_keywords) or 'none'} ({result.profile_fit}/10)",
    ]
    job.score_breakdown = result
    return job
