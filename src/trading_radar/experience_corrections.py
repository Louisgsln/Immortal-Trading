"""Explicit offline corrections using individually audited experience evidence."""

import html

from trading_radar.ca_cib import ca_experience_evidence
from trading_radar.greenhouse_filtered import jump_track_record_evidence
from trading_radar.macquarie_experience import macquarie_sales_trading_evidence
from trading_radar.models import Job, RawJob
from trading_radar.normalizer import canonical_url
from trading_radar.scoring import score_job


def correct_jump_experience(job: Job, keywords: dict[str, list[str]]) -> Job:
    """Prepare a copy for review; never write a job or invent a source observation.

    Only replace a legacy value reproducible from the audited coding phrase.
    Unexpected existing evidence or minima require investigation, not overwriting.
    Persist accepted results with ``Repository.update_derived_experience`` inside
    a locked transaction after reviewing and backing up the complete plan.
    """
    result = job.model_copy(deep=True)
    if (
        job.source != "jump_trading"
        or job.source_type != "official"
        or job.company_normalized != "jump trading"
    ):
        return result
    evidence = jump_track_record_evidence(job.description)
    if not evidence:
        return result
    professional = max(
        (item.minimum_years for item in evidence if item.kind == "professional"), default=None
    )
    legacy = max(item.minimum_years for item in evidence)
    if job.minimum_experience_years not in {legacy, professional}:
        raise ValueError("Stored Jump minimum does not match the audited derivation")
    if job.experience_evidence and job.experience_evidence != evidence:
        raise ValueError("Stored Jump evidence differs from the description; review required")
    result.minimum_experience_years = professional
    result.experience_evidence = evidence
    return score_job(result, keywords)


def correct_ca_experience(job: Job, archived: RawJob, keywords: dict[str, list[str]]) -> Job:
    """Attach a published field only when its archived identity and text agree.

    The archived collection retains named employer fields absent from stored
    descriptions. Never infer that provenance from an unlabelled number in text.
    """
    result = job.model_copy(deep=True)
    if (
        job.source != "credit_agricole_cib"
        or job.source_type != "official"
        or job.company_normalized != "credit agricole cib"
    ):
        return result
    if (
        not job.external_id
        or archived.external_id != job.external_id
        or archived.source != job.source
        or archived.source_type != job.source_type
        or archived.company != job.company
        or archived.title != job.title
        or canonical_url(archived.apply_url) != job.apply_url
        or archived.description != job.description
    ):
        raise ValueError("CA archive identity or description differs from the stored job")
    fields = (archived.raw_payload or {}).get("fields")
    if not isinstance(fields, dict) or any(
        not isinstance(key, str) or not isinstance(value, str) for key, value in fields.items()
    ):
        raise ValueError("CA archive lacks validated named fields")
    rebuilt = "\n".join(
        "<p>" + html.escape(value) + "</p>"
        for key, value in fields.items()
        if value and key.startswith(("fldjobdescription_", "fldapplicantcriteria_"))
    )
    if rebuilt != archived.description or fields.get("fldjobdescription_jobtitle") != job.title:
        raise ValueError("CA archived fields do not reproduce the retained description")
    evidence = ca_experience_evidence(fields.get("fldapplicantcriteria_experiencelevel", ""))
    if not evidence:
        return result
    if job.minimum_experience_years != evidence[0].minimum_years:
        raise ValueError("CA published minimum differs from the stored value")
    if job.experience_evidence and job.experience_evidence != evidence:
        raise ValueError("CA stored evidence requires review")
    result.experience_evidence = evidence
    return score_job(result, keywords)


def correct_macquarie_experience(job: Job, keywords: dict[str, list[str]]) -> Job:
    """Prepare the bounded sales-trading correction from preserved paragraphs."""
    result = job.model_copy(deep=True)
    if (
        job.source != "macquarie"
        or job.source_type != "official"
        or job.company_normalized != "macquarie"
    ):
        return result
    evidence = macquarie_sales_trading_evidence(job.description)
    if not evidence:
        return result
    minimum = max(item.minimum_years for item in evidence)
    if job.minimum_experience_years not in {None, minimum}:
        raise ValueError("Macquarie existing minimum requires review")
    if job.experience_evidence and job.experience_evidence != evidence:
        raise ValueError("Macquarie stored evidence requires review")
    result.minimum_experience_years = minimum
    result.experience_evidence = evidence
    return score_job(result, keywords)
