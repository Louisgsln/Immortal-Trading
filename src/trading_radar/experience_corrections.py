"""Explicit, offline correction of the audited Jump coding derivation."""

from trading_radar.greenhouse_filtered import jump_track_record_evidence
from trading_radar.models import Job
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
