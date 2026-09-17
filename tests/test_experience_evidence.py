"""Regression cases for literal applicant experience evidence, not employer history."""

import pytest

from trading_radar.greenhouse_filtered import (
    GreenhouseOptions,
    jump_track_record_minimum,
    parse_board,
)
from trading_radar.normalizer import normalize
from trading_radar.scoring import required_experience_years, score_job


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Requires 8 years experience.", [8]),
        ("At least 2-5+ years of experience in production engineering.", [2]),
        ("At least 2 – 5+ years of experience in production engineering.", [2]),
        ("2—5+ years of relevant experience required.", [2]),
        ("2-5 years experience is required.", [2]),
        ("Minimum of 3 years of analyst experience.", [3]),
        ("Must have 5 years’ experience.", [5]),
        ("8+ years hands-on experience.", [8]),
        ("Minimum 5 years working in a trading team.", [5]),
        ("7+ years of systematic trading experience, preferably in futures.", [7]),
        ("5+ years of analyst experience in power markets.", [5]),
        ("Have 3+ years of analyst experience in commodity analysis or trading.", [3]),
        ("5+ years of experience preferred.", []),
        ("Preferably 5+ years of experience.", []),
        ("5+ years of experience is a plus.", []),
        ("5+ years of experience is advantageous.", []),
        ("5+ years of experience is not required.", []),
        ("Requires 2 years experience; 5+ years of experience preferred.", [2]),
        ("Our firm has 25+ years of experience.", []),
        ("Our company has at least 25 years of experience.", []),
        ("Our company requires 5 years of experience.", [5]),
        ("Our business has a 25-year track record.", []),
        ("Our company has 25+ years of experience. Requires 3 years experience.", [3]),
        ("At least 5-2 years experience.", []),
        ("15+ years of experience.", [15]),
    ],
)
def test_experience_lower_bounds(text, expected):
    assert required_experience_years(text) == expected


def test_range_upper_bound_does_not_exclude_junior(raw, config):
    raw.description = "At least 2-5+ years of experience in production engineering."
    job = score_job(normalize(raw), config.keywords)
    assert job.score_breakdown.junior == 20
    assert "requires at least 5 years of experience" not in job.score_breakdown.exclusions


def test_preference_does_not_erase_separate_requirement(raw, config):
    raw.description = "Requires 5 years experience. Experience with Python is preferred."
    assert (
        "requires at least 5 years of experience"
        in score_job(normalize(raw), config.keywords).score_breakdown.exclusions
    )


TRACK = (
    "5+ year track record of solving challenging problems through coding "
    "with real metrics in industry."
)


@pytest.mark.parametrize("apostrophe", ["'", "’", "\ufffd"])
def test_jump_required_track_record(apostrophe):
    assert jump_track_record_minimum(f"<h2>Skills You{apostrophe}ll Need</h2><p>{TRACK}</p>") == 5


@pytest.mark.parametrize(
    "text",
    [
        TRACK,
        f"About us: {TRACK} Skills You'll Need: Python.",
        f"Skills You'll Need: Python. Nice to Have: {TRACK}",
        f"Skills You'll Need: Python. Preferred Qualifications: {TRACK}",
        "Skills You'll Need: 5+ year track record of investment returns.",
        f"Skills You'll Need: Preferably {TRACK}",
        "Skills You'll Need: " + TRACK.rstrip(".") + " is advantageous.",
        "Skills You'll Need: " + TRACK.rstrip(".") + " is a plus.",
        "Skills You'll Need: 2-5+ year track record of solving challenging problems through coding.",
        "Skills You'll Need: 2 - 5+ year track record of solving challenging problems through coding.",
        "Skills You'll Need: Our firm has " + TRACK,
        f"Skills You'll Need: {TRACK} Skills You'll Need: Python.",
    ],
)
def test_jump_does_not_infer_track_record_minimum(text):
    assert jump_track_record_minimum(text) is None


def test_jump_parser_passes_required_track_record_to_scoring():
    from trading_radar.config import load_config

    config = load_config()
    company = config.companies["jump_trading"]
    row = {
        "id": 6172858,
        "internal_job_id": 1,
        "title": "Quantitative Developer / Trading team",
        "company_name": "Jump Trading",
        "absolute_url": "https://www.jumptrading.com/hr/job?gh_jid=6172858",
        "metadata": [{"name": "Employment Type", "value": "Full-time - Experienced"}],
        "location": {"name": "Hong Kong"},
        "content": f"<h2>Skills You'll Need</h2><p>{TRACK}</p>",
    }
    jobs = parse_board(
        {"jobs": [row], "meta": {"total": 1}},
        "jump_trading",
        company,
        GreenhouseOptions(**company.options),
    )
    assert jobs[0].minimum_experience_years == 5
    scored = score_job(normalize(jobs[0]), config.keywords)
    assert "requires at least 5 years of experience" in scored.score_breakdown.exclusions
    assert scored.score_breakdown.junior == 0
