"""Employer programme facts, separate from the owner's targeting policy.

Full time describes working hours and does not contradict an internship title.
Publication and graduation dates never establish an intake year.
"""

import re

from trading_radar.config import Company, Settings
from trading_radar.internship_evidence import explicit_jane_street_internship
from trading_radar.models import Job
from trading_radar.normalizer import has, normalize_text
from trading_radar.opportunity_facts import duration_facts
from trading_radar.start_dates import start_period

INTERNSHIP_TERMS = {
    "internship",
    "internships",
    "intern",
    "interns",
    "stagiaire",
    "stage",
    "summer analyst",
    "summer associate",
    "off cycle",
    "offcycle",
}
APPRENTICE_TERMS = {"apprentice", "apprenticeship", "alternance", "alternant"}


def programme(job: Job) -> dict:
    title = job.title_normalized
    contract = normalize_text(job.employment_type or "")
    evidence = []
    issues = []
    kind = "unspecified"
    title_intern = any(has(title, term) for term in INTERNSHIP_TERMS)
    contract_intern = any(has(contract, term) for term in ["internship", "intern", "stage"])
    description_intern = explicit_jane_street_internship(job)
    if any(has(title + " " + contract, term) for term in APPRENTICE_TERMS):
        kind = "apprenticeship"
    elif any(
        has(title, term) for term in ["discovery program", "spring insight", "insight programme"]
    ):
        kind = "discovery"
    elif title_intern or contract_intern or description_intern:
        kind = "internship"
        if title_intern:
            evidence.append(job.title)
        if contract_intern:
            evidence.append("Contrat employeur : " + (job.employment_type or ""))
        if description_intern:
            evidence.append("Description Jane Street : stage explicitement annoncé au candidat")
        # SIG's New Graduates category and INTERN contract are contradictory.
        # These typed fields survive store_raw=False; a junior hint elsewhere
        # alone is not evidence of a contradictory programme.
        if (
            job.source == "sig"
            and job.seniority_hint == "junior"
            and contract_intern
            and not title_intern
        ):
            issues.append("Catégorie New Graduates et contrat de stage contradictoires")
    elif has(title, "graduate") or has(title, "new grad"):
        kind = "graduate"
    elif has(title, "vie") or has(title, "v i e"):
        kind = "vie"

    formats = []
    if kind == "internship":
        if has(title, "summer") or has(title, "ete") or has(contract, "summer"):
            formats.append("summer")
        if any(
            has(value, term) for value in (title, contract) for term in ("off cycle", "offcycle")
        ):
            formats.append("off_cycle")
        duration = duration_facts(job)
        if duration["precision"] == "conflict":
            issues.append("Durées de programme contradictoires")
        elif (
            duration["precision"] == "months"
            and 6 <= duration["min_months"] <= duration["max_months"] <= 12
        ):
            formats.append("long")
            evidence.extend(duration["evidence"])
        if "summer" in formats and any(f in formats for f in ["off_cycle", "long"]):
            issues.append("Formats de stage contradictoires")
    period = start_period(job) if kind == "internship" else {}
    years = (
        {int(y) for y in re.findall(r"\b20\d{2}\b", job.title)} if kind == "internship" else set()
    )
    if re.search(r"\b(?:graduating|graduation|graduates|class of)\b.{0,30}\b20\d{2}\b", title):
        years = set()
    if period.get("year"):
        years.add(period["year"])
    if period.get("precision") == "conflict" or len(years) > 1:
        issues.append("Années ou dates de début contradictoires")
    year = next(iter(years)) if len(years) == 1 else None
    evidence.extend(period.get("evidence", []))
    return {
        "kind": kind,
        "formats": list(dict.fromkeys(formats)),
        "year": year,
        "year_status": "conflict" if issues else "confirmed" if year else "unknown",
        "evidence": list(dict.fromkeys(evidence))[:10],
        "issues": issues,
    }


def internship_selected(observed: dict, settings: Settings) -> bool:
    return bool(
        settings.include_internships
        and observed["kind"] == "internship"
        and not observed["issues"]
        and "summer" not in observed["formats"]
        and (not observed["formats"] or set(observed["formats"]) & set(settings.internship_formats))
        and observed["year"] in {None, settings.internship_target_year}
    )


def programme_alertable(job: Job, settings: Settings) -> bool:
    observed = programme(job)
    if observed["kind"] in {"apprenticeship", "discovery"}:
        return False
    if observed["kind"] != "internship":
        return True
    return not internship_policy_reasons(observed, settings)


def internship_policy_reasons(observed: dict, settings: Settings) -> list[str]:
    """Explain the exact internship policy used by the scanner and delivery."""
    reasons = []
    if not settings.include_internships:
        reasons.append("internships_disabled")
    if not settings.internship_alerts_enabled:
        reasons.append("internship_alerts_disabled")
    if observed["issues"] or observed["year_status"] == "conflict":
        reasons.append("programme_conflict")
    if "summer" in observed["formats"]:
        reasons.append("summer_excluded")
    if not observed["formats"]:
        reasons.append("format_unconfirmed")
    elif not set(observed["formats"]) & set(settings.internship_formats):
        reasons.append("format_outside_scope")
    if observed["year_status"] != "confirmed" or observed["year"] is None:
        reasons.append("year_unconfirmed")
    elif observed["year"] != settings.internship_target_year:
        reasons.append("year_outside_scope")
    return reasons


def programme_company(company: Company, settings: Settings) -> Company:
    """Expand only internship exclusions, retaining employer and role scope."""
    if not settings.include_internships:
        return company
    updated = company.model_copy(deep=True)
    terms = updated.options.get("exclude_title_terms")
    if isinstance(terms, list):
        updated.options["exclude_title_terms"] = [
            term
            for term in terms
            if not isinstance(term, str) or normalize_text(term) not in INTERNSHIP_TERMS
        ]
    return updated
