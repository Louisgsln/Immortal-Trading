import pytest

from trading_radar.experience_corrections import correct_jump_experience
from trading_radar.models import ExperienceEvidence
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def legacy(raw, config, years=5, domain="industry and/or academia"):
    raw.company = "Jump Trading"
    raw.source = "jump_trading"
    raw.source_type = "official"
    raw.title = "Quantitative Developer"
    raw.minimum_experience_years = years
    raw.description = (
        "<h3>Skills You’ll Need</h3><p>"
        f"{years}+ year track record of solving challenging problems through coding "
        f"with real metrics &amp; impact in {domain}.</p>"
    )
    return score_job(normalize(raw), config.keywords)


@pytest.mark.parametrize(
    ("years", "domain", "expected"), [(5, "industry and/or academia", None), (2, "industry", 2)]
)
def test_repair_is_pure_bounded_and_idempotent(raw, config, years, domain, expected):
    old = legacy(raw, config, years, domain)
    before = old.model_dump()
    new = correct_jump_experience(old, config.keywords)
    assert old.model_dump() == before
    assert new.minimum_experience_years == expected
    assert new.experience_evidence[0].minimum_years == years
    assert new.score_breakdown.total == old.score_breakdown.total == 0
    assert "software role without embedded trading evidence" in new.score_breakdown.exclusions
    if expected is None:
        assert "requires at least 5 years of experience" not in new.score_breakdown.exclusions
    for key in before.keys() - {
        "minimum_experience_years",
        "experience_evidence",
        "score_breakdown",
    }:
        assert before[key] == new.model_dump()[key]
    assert correct_jump_experience(new, config.keywords) == new


@pytest.mark.parametrize(
    ("field", "value"),
    [("source", "other"), ("source_type", "board"), ("company_normalized", "other")],
)
def test_no_repairs_outside_official_jump_source(raw, config, field, value):
    old = legacy(raw, config)
    setattr(old, field, value)
    assert correct_jump_experience(old, config.keywords) == old


def test_unknown_minimum_is_not_overwritten(raw, config):
    old = legacy(raw, config)
    old.minimum_experience_years = 9
    with pytest.raises(ValueError, match="minimum does not match"):
        correct_jump_experience(old, config.keywords)
    assert old.minimum_experience_years == 9


def test_different_existing_evidence_requires_review(raw, config):
    old = legacy(raw, config)
    old.experience_evidence = [
        ExperienceEvidence(minimum_years=5, kind="professional", excerpt="Another source phrase")
    ]
    with pytest.raises(ValueError, match="evidence differs"):
        correct_jump_experience(old, config.keywords)


def test_no_matching_phrase_does_not_remove_an_existing_minimum(raw, config):
    old = legacy(raw, config)
    old.description = "Other requirements"
    assert correct_jump_experience(old, config.keywords) == old
