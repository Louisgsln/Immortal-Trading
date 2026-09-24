import html

import pytest

from tests.test_nomura_professionals import company, detail, row
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.experience_corrections import correct_nomura_experience
from trading_radar.models import ExperienceEvidence
from trading_radar.nomura_experience import nomura_experience_evidence
from trading_radar.nomura_professionals import parse_detail, role_metadata
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def table(value, grade="Analyst"):
    return f"Position Specifications: Corporate Title {grade} Functional Title Analyst Experience {value} Qualification Degree or equivalent. Role & Responsibilities: Trading."


@pytest.mark.parametrize(
    "value,years",
    [
        ("1-3 years", 1),
        ("2 - 4 years", 2),
        ("2 - 10 years", 2),
        ("3 -5 years", 3),
        ("0-2 years of experience preferably in Securitisation Market covering ABS/RMBS/CMBS", 0),
        (
            "3-5 years of experience preferably in Securitisation Market covering ABS/RMBS/CMBS in European or US markets",
            3,
        ),
        (
            "2+ years of experience in Securitisation Market covering ABS/RMBS/CMBS in European or US markets",
            2,
        ),
    ],
)
def test_audited_fields_preserve_exact_excerpt_and_minimum(value, years):
    text = table(value)
    [proof] = nomura_experience_evidence(text)
    assert proof.model_dump() == {
        "minimum_years": years,
        "kind": "professional",
        "origin": "description",
        "method": "nomura_position_specifications",
        "excerpt": "Experience " + value,
    }
    assert proof.excerpt in text
    assert role_metadata(text)[2] == years


@pytest.mark.parametrize(
    "value",
    [
        "5-2 years",
        "5+ years preferred",
        "preferably 5 years",
        "no experience required",
        "5 years or an advanced degree",
        "5 years or 2 years with a Master's",
        "5 years of academic experience",
        "5 years of experience is not required",
        "5 years maximum",
        "up to 5 years",
        "-2 years",
        "100 years",
        "2.5 years",
        "5 years (optional)",
        "5 years Experience 2 years",
        "5 years in another field",
    ],
)
def test_ambiguous_or_unaudited_fields_do_not_gain_provenance(value):
    assert nomura_experience_evidence(table(value)) == []


@pytest.mark.parametrize(
    "text",
    [
        "Preferred Experience: 5+ years in trading.",
        "Experience: 5-2 years.",
        "Qualification: a degree or Experience: 5 years.",
        "Experience 5 years preferred.",
        "No Experience 5 years is required.",
        "Experience 5 years is not required.",
        "Experience 5 years or 2 years with a degree.",
        "Company Experience 50 years.",
        '"Experience 5 years" is an example.',
        "Contract duration: 2 years.",
    ],
)
def test_legacy_false_positive_cases_no_longer_supply_a_minimum(text):
    assert role_metadata(text)[2] is None
    assert nomura_experience_evidence(text) == []


@pytest.mark.parametrize(
    "transform",
    [
        lambda text: text.replace("Position Specifications:", "About the company:"),
        lambda text: text.replace("Functional Title", "Role & Responsibilities"),
        lambda text: text.replace("Functional Title", "Other Label"),
        lambda text: text.replace("Experience", "Role & Responsibilities: Experience"),
        lambda text: text.replace("Corporate Title", "Someone else's Corporate Title"),
        lambda text: text.replace("Experience", "Preferred Experience"),
        lambda text: text.replace("Qualification", "Role & Responsibilities"),
        lambda text: text + " " + text,
        lambda text: "Preferred " + text,
        lambda text: '"' + text + '"',
    ],
)
def test_table_context_required_and_ambiguous_tables_rejected(transform):
    assert nomura_experience_evidence(transform(table("2-4 years"))) == []


def test_outside_table_minimum_retained_without_invented_provenance():
    text = "Experience 4-8 years of experience in Malaysian Equity products Excellent Written and Verbal communication skills."
    assert role_metadata(text)[2] == 4
    assert nomura_experience_evidence(text) == []


@pytest.mark.parametrize("grade,seniority", [("Analyst", "junior"), ("Vice President", "senior")])
def test_collector_propagates_proof_and_keeps_grade_independent(config, grade, seniority):
    raw = parse_detail(
        detail(row(), table("3-5 years", grade)), row(), company(), "nomura_professionals"
    )
    assert raw.seniority_hint == seniority and raw.minimum_experience_years == 3
    assert raw.experience_evidence[0].excerpt == "Experience 3-5 years"
    job = score_job(normalize(raw), config.keywords)
    assert job.experience_evidence == raw.experience_evidence
    if seniority == "senior":
        assert job.score_breakdown.total == 0


def legacy_job(config, raw):
    raw.company = "Nomura"
    raw.source = "nomura_professionals"
    raw.source_type = "official"
    raw.description = "<p>" + html.escape(table("2-4 years")) + "</p>"
    raw.minimum_experience_years = 2
    return score_job(normalize(raw), config.keywords)


def test_backfill_changes_only_provenance_and_is_idempotent(config, raw, repo, tmp_path):
    old = legacy_job(config, raw)
    before = old.model_dump()
    new = correct_nomura_experience(old)
    assert old.model_dump() == before
    assert {key for key in before if before[key] != new.model_dump()[key]} == {
        "experience_evidence"
    }
    assert correct_nomura_experience(new) == new
    with repo.transaction():
        repo.upsert(old)
    repo.update_application(old.id, {"status": "Interview", "notes": "À conserver"})
    application = repo.application(old.id)
    with repo.transaction():
        assert repo.update_derived_experience(new)
        assert not repo.update_derived_experience(new)
    assert repo.application(old.id) == application
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    exported = build_dashboard_data(config)["jobs"][0]
    assert exported["experience"]["evidence"] == [
        item.model_dump(mode="json") for item in new.experience_evidence
    ]
    assert exported["score"] == old.score_breakdown.total


@pytest.mark.parametrize(
    "field,value", [("source", "other"), ("source_type", "board"), ("company_normalized", "other")]
)
def test_backfill_never_touches_other_sources(config, raw, field, value):
    job = legacy_job(config, raw)
    setattr(job, field, value)
    assert correct_nomura_experience(job) == job


def test_backfill_refuses_unexpected_minimum_or_evidence(config, raw):
    job = legacy_job(config, raw)
    job.minimum_experience_years = 9
    with pytest.raises(ValueError, match="minimum differs"):
        correct_nomura_experience(job)
    job.minimum_experience_years = 2
    job.experience_evidence = [
        ExperienceEvidence(
            minimum_years=5,
            kind="professional",
            method="nomura_position_specifications",
            excerpt="Other source text",
        )
    ]
    with pytest.raises(ValueError, match="evidence requires review"):
        correct_nomura_experience(job)


@pytest.mark.parametrize(
    "origin,kind",
    [
        ("employer_field", "professional"),
        ("description", "unspecified"),
        ("description", "industry_or_academia"),
    ],
)
def test_model_does_not_allow_wrong_nomura_provenance(origin, kind):
    with pytest.raises(ValueError):
        ExperienceEvidence(
            minimum_years=2,
            method="nomura_position_specifications",
            origin=origin,
            kind=kind,
            excerpt="Experience 2-4 years",
        )
