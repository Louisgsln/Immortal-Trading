import pytest

from trading_radar.internship_evidence import (
    INTERNSHIP_EXCLUSION,
    explicit_jane_street_internship,
)
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def candidate(raw, description):
    raw.company = "Jane Street"
    raw.source = "jane_street"
    raw.source_type = "official"
    raw.title = "Quantitative Trader"
    raw.description = description
    raw.employment_type = None
    return normalize(raw)


@pytest.mark.parametrize(
    "description",
    [
        "As an intern, you are paired with full-time employees who act as mentors.",
        "As an intern, you'll be paired with full-time employees.",
        "As a Data Engineering intern, you'll learn how we turn messy data into foundations.",
        "About the Position As a Sales and Trading intern, you’ll work alongside our Sales people.",
        "About the Position: As an SP Intern, you'll work on projects.",
        'As a quantitative trading intern, you\'ll also have one "elective" based on your interests.',
        "During the internship, your work is reinforced with intensive classes.",
        "During the internship, you will work in collaboration with your mentors.",
        "During the internship you'll take on two real projects.",
        "Over the course of your internship, you will explore ways to improve our systems.",
        "You'll spend the bulk of your internship working closely with full-time researchers.",
        "You’ll spend the bulk of your internship working closely with full-time researchers.",
        "You will spend the bulk of your internship working closely with full-time researchers.",
        "We provide education. As a Linux Engineering intern, you’ll work with full-timers.",
        "Our work is open-source; During the internship, you will work on one project.",
        "About the Position\nAs an intern, you are paired with full-time employees.",
    ],
)
def test_current_recipient_internship_is_explicit(raw, description):
    job = candidate(raw, description)
    original = job.model_dump(mode="json")
    assert explicit_jane_street_internship(job)
    assert job.model_dump(mode="json") == original


@pytest.mark.parametrize(
    "description",
    [
        "As an intern, you were paired with mentors.",
        "As an intern, you had worked on projects.",
        "During the internship, you worked with researchers.",
        "Over the course of your internship, you were working with researchers.",
        "You spent the bulk of your internship working with researchers.",
        "As a former intern, you are familiar with our systems.",
        "As an intern, you are expected to have worked here last summer.",
        "Previously, as an intern, you are paired with mentors.",
        "If selected, as an intern, you will work on projects.",
        "As an intern, you would work on projects.",
        "As an intern, you will work on projects if you apply for that programme.",
        "As an intern, you will not work on trading projects.",
        "During the internship, you will never work with this team.",
        "As an intern, you are no longer employed here.",
        "During the internship, you will mentor our interns.",
        "During the internship, you will work as a mentor.",
        "You will supervise interns on the trading desk.",
        "We hire outstanding interns; you will run our internship recruitment pipeline.",
        "Internship experience is desirable for this full-time permanent trading role.",
        "Skills gained through academic studies, internships, or employment are welcome.",
        "Since our inception as a skunkworks intern project in late 2015, we have grown.",
        "Our previous advert said: As an intern, you will work with researchers.",
        '"As an intern, you will work with researchers." This position is permanent.',
        "“As an intern, you will work with researchers.” This position is permanent.",
        "'As an intern, you'll work with researchers.' This position is permanent.",
        "‘As an intern, you will work with researchers.’ This position is permanent.",
        '"A former advert. As an intern, you will work with researchers." Permanent role.',
        "See our internship programme: As an intern, you will work with researchers.",
        "As an internal trader, you will work with researchers.",
        "As an internship mentor, you will guide researchers.",
        "This permanent role does not require internship experience.",
    ],
)
def test_history_other_people_conditions_negations_and_quotes_are_not_evidence(raw, description):
    assert not explicit_jane_street_internship(candidate(raw, description))


@pytest.mark.parametrize(
    "changes",
    [
        {"source": "fixture"},
        {"source_type": "ats"},
        {"source_type": "board"},
        {"company_normalized": "jump trading"},
    ],
)
def test_rule_only_applies_to_audited_official_source(raw, changes):
    job = candidate(raw, "As an intern, you will work with researchers.")
    for key, value in changes.items():
        setattr(job, key, value)
    assert not explicit_jane_street_internship(job)


def test_scoring_excludes_internship_without_rewriting_source_attributes(raw, config):
    job = candidate(
        raw, "As a quantitative trading intern, you'll work with researchers. FX Python."
    )
    source_fields = {
        name: getattr(job, name)
        for name in (
            "description",
            "description_text",
            "employment_type",
            "seniority_hint",
            "expected_start_date",
            "title",
            "title_normalized",
            "source",
            "source_type",
        )
    }
    scored = score_job(job, config.keywords)
    assert scored.score_breakdown.total == 0
    assert INTERNSHIP_EXCLUSION in scored.score_breakdown.exclusions
    assert {name: getattr(scored, name) for name in source_fields} == source_fields


def test_contract_and_existing_role_exclusions_are_preserved(raw, config):
    job = candidate(raw, "As an intern, you are paired with full-time researchers.")
    job.title = "Fundamental Research Analyst"
    job.title_normalized = "fundamental research analyst"
    job.employment_type = "Internship"
    exclusions = score_job(job, config.keywords).score_breakdown.exclusions
    assert INTERNSHIP_EXCLUSION in exclusions
    assert "internship or apprenticeship contract" in exclusions
    assert "research analyst" in exclusions
