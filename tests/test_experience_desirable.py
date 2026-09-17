"""Bound the directly attached experience preference observed in the lot 28 audit."""

import pytest

from trading_radar.normalizer import normalize
from trading_radar.scoring import required_experience_years, score_job


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "Experience Desirable: 1+ years of relevant experience in banking, "
            "preferably in Project Finance and Digital Infrastructure",
            [],
        ),
        ("EXPERIENCE DESIRABLE: 5+ years of relevant experience.", []),
        ("Experience Desirable: Minimum of 5 years of experience.", []),
        ("Experience Desirable: At least 2-5+ years of relevant experience.", []),
        ("Education Desirable: Finance degree, 5+ years of experience.", [5]),
        ("Experience Desirable: Python. Requires 3 years experience.", [3]),
        ("Experience Desirable: Python; 5+ years of experience.", [5]),
        ("Experience Desirable: Python, 5+ years of experience.", [5]),
        ("Experience Desirable:\n5+ years of experience.", [5]),
        ("Experience Desirable: 1+ years of experience. Requires 3 years experience.", [3]),
        ("Requires 5 years experience. Experience Desirable: 1+ years of experience.", [5]),
    ],
)
def test_experience_desirable_attaches_only_to_adjacent_requirement(text, expected):
    assert required_experience_years(text) == expected


def test_structured_minimum_survives_desirable_experience(raw, config):
    raw.description = "Experience Desirable: 5+ years of relevant experience."
    raw.minimum_experience_years = 5
    scored = score_job(normalize(raw), config.keywords)
    assert required_experience_years(scored.description_text) == []
    assert scored.score_breakdown.junior == 0
    assert "requires at least 5 years of experience" in scored.score_breakdown.exclusions


def test_desirable_experience_preserves_junior_evidence(raw, config):
    raw.description = "Experience Desirable: 5+ years of relevant experience."
    raw.minimum_experience_years = 0
    scored = score_job(normalize(raw), config.keywords)
    assert scored.score_breakdown.junior == 20
    assert "requires at least 5 years of experience" not in scored.score_breakdown.exclusions
