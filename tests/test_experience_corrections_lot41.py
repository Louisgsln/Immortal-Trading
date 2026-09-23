import html

import pytest

from trading_radar.experience_corrections import correct_ca_experience, correct_macquarie_experience
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def ca_pair(raw, config, minimum=0):
    fields = {
        "fldjobdescription_jobtitle": "Trading Analyst",
        "fldjobdescription_description1": "Trading derivatives. Python.",
        "fldapplicantcriteria_experiencelevel": f"{minimum}-{minimum + 2} years",
    }
    archive = raw.model_copy(deep=True)
    archive.company = "Crédit Agricole CIB"
    archive.source = "credit_agricole_cib"
    archive.source_type = "official"
    archive.external_id = "2026-123456"
    archive.title = fields["fldjobdescription_jobtitle"]
    archive.description = "\n".join("<p>" + html.escape(v) + "</p>" for v in fields.values())
    archive.raw_payload = {"fields": fields}
    item = normalize(archive)
    item.minimum_experience_years = minimum
    return score_job(item, config.keywords), archive


@pytest.mark.parametrize("minimum", [0, 3, 6, 11])
def test_ca_backfill_preserves_minimum_score_source_and_archive(raw, config, minimum):
    old, archive = ca_pair(raw, config, minimum)
    snapshot, captured = old.model_dump(), archive.model_dump()
    new = correct_ca_experience(old, archive, config.keywords)
    assert old.model_dump() == snapshot and archive.model_dump() == captured
    assert new.minimum_experience_years == minimum
    assert new.score_breakdown == old.score_breakdown
    assert new.experience_evidence[0].origin == "employer_field"
    assert new.experience_evidence[0].excerpt == f"{minimum}-{minimum + 2} years"
    assert {k for k in snapshot if snapshot[k] != new.model_dump()[k]} == {"experience_evidence"}
    assert correct_ca_experience(new, archive, config.keywords) == new


@pytest.mark.parametrize(
    "field", ["external_id", "title", "company", "source", "description", "apply_url"]
)
def test_ca_archive_mismatch_refuses_backfill(raw, config, field):
    old, archive = ca_pair(raw, config)
    setattr(archive, field, "https://example.com/other" if field == "apply_url" else "different")
    with pytest.raises(ValueError, match="identity or description"):
        correct_ca_experience(old, archive, config.keywords)
    assert old.experience_evidence == []


def test_ca_tampered_named_field_is_not_inferred_from_unlabelled_text(raw, config):
    old, archive = ca_pair(raw, config)
    archive.raw_payload["fields"]["fldapplicantcriteria_experiencelevel"] = "6-10 years"
    with pytest.raises(ValueError, match="fields do not reproduce"):
        correct_ca_experience(old, archive, config.keywords)


def test_ca_unexpected_stored_minimum_is_not_overwritten(raw, config):
    old, archive = ca_pair(raw, config)
    old.minimum_experience_years = 8
    with pytest.raises(ValueError, match="minimum differs"):
        correct_ca_experience(old, archive, config.keywords)


def macquarie_job(raw, config):
    raw.company = "Macquarie"
    raw.source = "macquarie"
    raw.source_type = "official"
    raw.title = "Institutional Cash Equity Sales Trader"
    raw.description = "<p>5 years’ of experience in sales trading, including client coverage.</p>"
    raw.minimum_experience_years = None
    return score_job(normalize(raw), config.keywords)


def test_macquarie_correction_changes_only_derived_fields_and_is_idempotent(raw, config):
    old = macquarie_job(raw, config)
    before = old.model_dump()
    assert old.score_breakdown.total > 0
    new = correct_macquarie_experience(old, config.keywords)
    assert new.minimum_experience_years == 5
    assert new.experience_evidence[0].method == "macquarie_sales_trading_experience"
    assert new.score_breakdown.total == 0
    assert "requires at least 5 years of experience" in new.score_breakdown.exclusions
    assert old.model_dump() == before
    assert {k for k in before if before[k] != new.model_dump()[k]} == {
        "minimum_experience_years",
        "experience_evidence",
        "score_breakdown",
    }
    assert correct_macquarie_experience(new, config.keywords) == new


def test_macquarie_unexpected_stronger_minimum_is_not_replaced(raw, config):
    old = macquarie_job(raw, config)
    old.minimum_experience_years = 8
    with pytest.raises(ValueError, match="existing minimum"):
        correct_macquarie_experience(old, config.keywords)


@pytest.mark.parametrize(
    ("field", "value"),
    [("source", "other"), ("source_type", "board"), ("company_normalized", "other")],
)
def test_corrections_are_bounded_to_official_sources(raw, config, field, value):
    ca, archive = ca_pair(raw, config)
    macquarie = macquarie_job(raw, config)
    setattr(ca, field, value)
    setattr(macquarie, field, value)
    assert correct_ca_experience(ca, archive, config.keywords) == ca
    assert correct_macquarie_experience(macquarie, config.keywords) == macquarie
