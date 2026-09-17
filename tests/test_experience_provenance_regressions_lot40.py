"""Independent provenance regressions for the two audited Jump coding records."""

import pytest

from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import (
    GreenhouseOptions,
    jump_track_record_evidence,
    jump_track_record_minimum,
    parse_board,
)
from trading_radar.models import ExperienceEvidence, Job, RawJob
from trading_radar.normalizer import normalize, plain_text
from trading_radar.scoring import required_experience_years, score_job

MIXED_RECORD = (
    "5+ year track record of solving challenging problems through coding with real "
    "metrics & impact in industry and/or academia."
)
PROFESSIONAL_RECORD = (
    "2+ year track record of solving challenging problems through coding with real "
    "metrics & impact in industry."
)


def _content(record):
    return "<h2>Skills You’ll Need</h2><p>" + record + "</p>"


def _parse(config, record, identifier):
    # Reproduce the public metadata shape, without relying on a local database.
    company = load_config().companies["jump_trading"]
    row = {
        "id": identifier,
        "internal_job_id": identifier + 1,
        "title": "Quantitative Developer | Trading team",
        "company_name": "Jump Trading",
        "absolute_url": f"https://www.jumptrading.com/hr/job?gh_jid={identifier}",
        "metadata": [{"name": "Employment Type", "value": "Full-time - Experienced"}],
        "location": {"name": "Hong Kong"},
        "content": _content(record),
    }
    return parse_board(
        {"jobs": [row], "meta": {"total": 1}},
        "jump_trading",
        company,
        GreenhouseOptions(**company.options),
    )[0]


@pytest.mark.parametrize(
    ("record", "years", "kind", "professional_minimum"),
    [
        pytest.param(MIXED_RECORD, 5, "industry_or_academia", None, id="jump-6172858"),
        pytest.param(PROFESSIONAL_RECORD, 2, "professional", 2, id="jump-7767735"),
        pytest.param(
            "5+ year track record of solving challenging problems through coding "
            "with real metrics.",
            5,
            "unspecified",
            None,
            id="practice-domain-unspecified",
        ),
        pytest.param(
            "0+ year track record of solving challenging problems through coding "
            "with real metrics & impact in industry.",
            0,
            "professional",
            0,
            id="professional-zero-is-explicit",
        ),
    ],
)
def test_evidence_keeps_years_domain_origin_and_exact_excerpt(
    record, years, kind, professional_minimum
):
    content = _content(record)
    evidence = jump_track_record_evidence(content)
    assert len(evidence) == 1
    item = evidence[0]
    assert isinstance(item, ExperienceEvidence)
    assert item.minimum_years == years
    assert item.kind == kind
    assert item.origin == "description"
    assert item.method == "jump_coding_track_record"
    assert item.excerpt in plain_text(content)
    assert record.rstrip(".") in item.excerpt
    assert jump_track_record_minimum(content) == professional_minimum


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(MIXED_RECORD, id="no-required-section"),
        pytest.param(
            "<h2>About Us</h2><p>" + MIXED_RECORD + "</p><h2>Skills You’ll Need</h2>Python",
            id="company-history-section",
        ),
        pytest.param(
            _content("Our company has a " + PROFESSIONAL_RECORD),
            id="company-history-in-required-section",
        ),
        pytest.param(_content("Preferably " + PROFESSIONAL_RECORD), id="leading-preference"),
        pytest.param(
            _content(PROFESSIONAL_RECORD.rstrip(".") + " is optional."),
            id="optional-record",
        ),
        pytest.param(
            _content(PROFESSIONAL_RECORD.rstrip(".") + " is not required."),
            id="negated-record",
        ),
        pytest.param(
            _content(PROFESSIONAL_RECORD.rstrip(".") + " is a plus."),
            id="record-is-a-plus",
        ),
        pytest.param(
            "<h2>Skills You’ll Need</h2>Python.<h2>Nice to Have</h2>" + PROFESSIONAL_RECORD,
            id="optional-section",
        ),
        pytest.param(
            _content(PROFESSIONAL_RECORD.replace("2+", "2-5+")),
            id="range-not-an-audited-single-minimum",
        ),
        pytest.param(
            _content(PROFESSIONAL_RECORD.replace("2+", "5–2+")),
            id="inverted-range",
        ),
        pytest.param(
            _content(PROFESSIONAL_RECORD.replace("2+", "2.5+")),
            id="decimal-not-trailing-five",
        ),
        pytest.param(
            _content(PROFESSIONAL_RECORD.replace("2+", "-2+")),
            id="negative-not-positive-two",
        ),
        pytest.param(
            _content(PROFESSIONAL_RECORD.replace("2+", "100+")),
            id="out-of-bounds-not-trailing-zero",
        ),
    ],
)
def test_optional_historical_negated_and_invalid_records_create_no_evidence(content):
    assert jump_track_record_evidence(content) == []
    assert jump_track_record_minimum(content) is None


def test_later_generic_preference_does_not_erase_the_mixed_coding_record(config):
    record = (
        MIXED_RECORD + " Passion for building efficient, modular software to tackle "
        "challenging problems. Experience is a plus, but a strong desire to learn "
        "and grow is essential."
    )
    raw = _parse(config, record, 6172858)
    assert raw.minimum_experience_years is None
    assert len(raw.experience_evidence) == 1
    assert raw.experience_evidence[0].minimum_years == 5
    assert raw.experience_evidence[0].kind == "industry_or_academia"
    assert raw.description == _content(record)
    assert raw.employment_type == "Full-time - Experienced"
    assert required_experience_years(plain_text(raw.description)) == []
    result = score_job(normalize(raw), config.keywords)
    assert result.score_breakdown.total == 0
    assert "software role without embedded trading evidence" in result.score_breakdown.exclusions
    assert "requires at least 5 years of experience" not in result.score_breakdown.exclusions
    assert result.experience_evidence == raw.experience_evidence


def test_industry_coding_record_keeps_two_years_and_software_exclusion(config):
    raw = _parse(config, PROFESSIONAL_RECORD, 7767735)
    assert raw.minimum_experience_years == 2
    assert raw.experience_evidence[0].kind == "professional"
    result = score_job(normalize(raw), config.keywords)
    assert result.score_breakdown.total == 0
    assert "software role without embedded trading evidence" in result.score_breakdown.exclusions
    assert result.minimum_experience_years == 2
    assert result.experience_evidence == raw.experience_evidence


def test_unknown_domain_does_not_become_five_professional_years(config):
    record = "5+ year track record of solving challenging problems through coding."
    raw = _parse(config, record, 6172858)
    assert raw.minimum_experience_years is None
    assert raw.experience_evidence[0].kind == "unspecified"
    result = score_job(normalize(raw), config.keywords)
    assert "requires at least 5 years of experience" not in result.score_breakdown.exclusions


def test_legacy_payload_does_not_silently_repair_stored_experience(config):
    raw = _parse(config, MIXED_RECORD, 6172858)
    payload = normalize(raw).model_dump(mode="json")
    payload.pop("experience_evidence")
    payload["minimum_experience_years"] = 5
    legacy = Job.model_validate(payload)
    assert legacy.experience_evidence == []
    assert legacy.minimum_experience_years == 5
    result = score_job(legacy, config.keywords)
    assert "requires at least 5 years of experience" in result.score_breakdown.exclusions
    assert result.score_breakdown.total == 0


def test_evidence_list_round_trips_and_default_lists_are_independent(config):
    raw = _parse(config, MIXED_RECORD, 6172858)
    assert RawJob.model_validate_json(raw.model_dump_json()) == raw
    old = raw.model_dump(mode="json")
    old.pop("experience_evidence")
    first = RawJob.model_validate(old)
    second = RawJob.model_validate(old)
    first.experience_evidence.append(raw.experience_evidence[0])
    assert second.experience_evidence == []
