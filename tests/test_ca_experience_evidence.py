import pytest
from pydantic import ValidationError

from trading_radar.ca_cib import ca_experience_evidence
from trading_radar.models import ExperienceEvidence


@pytest.mark.parametrize(
    ("value", "minimum"),
    [
        ("0 - 2 ans", 0),
        ("0-2 years", 0),
        ("3-5 years", 3),
        ("6 - 10 ans", 6),
        ("6-10 years", 6),
        ("11 ans et plus", 11),
        ("11 years and more", 11),
        ("0-0 years", 0),
        ("99-99 years", 99),
        ("99 ans et plus", 99),
    ],
)
def test_dedicated_experience_field_keeps_exact_value_and_lower_bound(value, minimum):
    [proof] = ca_experience_evidence(value)
    assert proof.model_dump() == {
        "minimum_years": minimum,
        "kind": "professional",
        "origin": "employer_field",
        "method": "ca_cib_experience_level",
        "excerpt": value,
    }


@pytest.mark.parametrize(
    "value",
    [
        "",
        "Experienced",
        "6 - 3 ans",
        "3-2 years",
        "100-101 years",
        "99-100 years",
        "100 years and more",
        "-1-2 years",
        "1.5-2 years",
        "1,5-2 years",
        "x3-5 years",
        "3-5+ years",
        "0–2 years",
        "0—2 years",
        "3 years",
        "3+ years",
        "0-2 years preferred",
        "Preferred 0-2 years",
        "3-5 years not required",
        "Bachelor degree or 3-5 years",
        "Our firm has 3-5 years",
        "Contract of 3-5 years",
        "3-5 years in trading",
        "0-2 years. 6-10 years",
        "<p>0-2 years</p>",
    ],
)
def test_unknown_preferences_alternatives_and_invalid_bounds_are_not_reinterpreted(value):
    assert ca_experience_evidence(value) == []


@pytest.mark.parametrize(
    ("method", "origin", "kind"),
    [
        ("jump_coding_track_record", "description", "professional"),
        ("jump_coding_track_record", "description", "industry_or_academia"),
        ("jump_coding_track_record", "description", "unspecified"),
        ("ca_cib_experience_level", "employer_field", "professional"),
        ("macquarie_sales_trading_experience", "description", "professional"),
    ],
)
def test_supported_origin_method_kind_combinations_roundtrip(method, origin, kind):
    value = {
        "minimum_years": 3,
        "method": method,
        "origin": origin,
        "kind": kind,
        "excerpt": "proof",
    }
    proof = ExperienceEvidence.model_validate(value)
    assert ExperienceEvidence.model_validate_json(proof.model_dump_json()).model_dump() == value


@pytest.mark.parametrize(
    ("method", "origin", "kind"),
    [
        ("jump_coding_track_record", "employer_field", "professional"),
        ("ca_cib_experience_level", "description", "professional"),
        ("ca_cib_experience_level", "employer_field", "industry_or_academia"),
        ("ca_cib_experience_level", "employer_field", "unspecified"),
        ("macquarie_sales_trading_experience", "employer_field", "professional"),
        ("macquarie_sales_trading_experience", "description", "industry_or_academia"),
        ("macquarie_sales_trading_experience", "description", "unspecified"),
    ],
)
def test_contradictory_provenance_is_rejected(method, origin, kind):
    with pytest.raises(ValidationError):
        ExperienceEvidence.model_validate(
            {
                "minimum_years": 3,
                "method": method,
                "origin": origin,
                "kind": kind,
                "excerpt": "proof",
            }
        )
