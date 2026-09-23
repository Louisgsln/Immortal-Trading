"""Independent regressions for audited CA fields and Macquarie sales trading."""

import pytest
from pydantic import ValidationError

from trading_radar.ca_cib import ca_experience_evidence
from trading_radar.macquarie_experience import macquarie_sales_trading_evidence
from trading_radar.models import ExperienceEvidence, RawJob
from trading_radar.normalizer import plain_text

MACQUARIE_REQUIREMENT = "5 years’ of experience in sales trading, including client coverage and new business development"
MACQUARIE_PARAGRAPH = (
    MACQUARIE_REQUIREMENT
    + " Proven ability to build and manage institutional client relationships, with "
    "interest in the hedge fund segment Strong account management skills and experience "
    "working in a global, team-oriented environment Solid understanding of risk management "
    "and trading operations in institutional equity markets Series 7, 63, and 55 licenses, "
    "with strong academic credentials, ideally in a quantitative or technology field"
)


@pytest.mark.parametrize(
    ("field", "minimum"),
    [
        ("0 - 2 ans", 0),
        ("0-2 years", 0),
        ("3-5 years", 3),
        ("6 - 10 ans", 6),
        ("6-10 years", 6),
        ("11 ans et plus", 11),
    ],
)
def test_exact_archived_ca_fields_keep_published_bounds_and_origin(field, minimum):
    evidence = ca_experience_evidence(field)
    assert [item.model_dump() for item in evidence] == [
        {
            "minimum_years": minimum,
            "kind": "professional",
            "origin": "employer_field",
            "method": "ca_cib_experience_level",
            "excerpt": field,
        }
    ]


@pytest.mark.parametrize(
    ("field", "minimum"),
    [("0-0 years", 0), ("99-99 years", 99), ("99 years and more", 99)],
)
def test_ca_model_bounds_are_inclusive_without_losing_the_published_field(field, minimum):
    [evidence] = ca_experience_evidence(field)
    assert evidence.minimum_years == minimum
    assert evidence.excerpt == field
    assert ExperienceEvidence.model_validate_json(evidence.model_dump_json()) == evidence


@pytest.mark.parametrize(
    "field",
    [
        "",
        "Experienced",
        "0-2 years preferred",
        "Preferred 0-2 years",
        "0-2 years not required",
        "A degree or 3-5 years",
        "Contract duration: 3-5 years",
        "6 - 3 ans",
        "3-2 years",
        "100-101 years",
        "-1-2 years",
        "1.5-2 years",
        "99-100 years",
        "100 ans et plus",
        "０-２ years",
        "0–2 years",
    ],
)
def test_ca_unknown_optional_alternative_contract_and_invalid_values_do_not_supply_proof(field):
    assert ca_experience_evidence(field) == []


def test_zero_employer_field_proof_survives_job_json_without_becoming_description_evidence():
    original = RawJob(
        company="Crédit Agricole CIB",
        title="Trading Analyst",
        apply_url="https://example.test/job",
        source="credit_agricole_cib",
        description="<p>0-2 years</p>",
        minimum_experience_years=0,
        experience_evidence=ca_experience_evidence("0-2 years"),
    )
    restored = RawJob.model_validate_json(original.model_dump_json())
    assert restored.minimum_experience_years == 0
    assert restored.experience_evidence == original.experience_evidence
    assert restored.experience_evidence[0].origin == "employer_field"
    legacy = original.model_dump(exclude={"experience_evidence"})
    assert RawJob.model_validate(legacy).experience_evidence == []


def test_real_macquarie_23225_requirement_survives_later_degree_preference():
    html = "<p>We operate across global markets.</p><p>" + MACQUARIE_PARAGRAPH + "</p>"
    evidence = macquarie_sales_trading_evidence(html)
    assert len(evidence) == 1
    assert evidence[0].model_dump() == {
        "minimum_years": 5,
        "kind": "professional",
        "origin": "description",
        "method": "macquarie_sales_trading_experience",
        "excerpt": MACQUARIE_REQUIREMENT,
    }
    assert evidence[0].excerpt in plain_text(html)
    assert "ideally" not in evidence[0].excerpt


@pytest.mark.parametrize("apostrophe", ["’", "'", ""])
def test_macquarie_apostrophe_variants_preserve_the_evidence(apostrophe):
    clause = f"5 years{apostrophe} of experience in sales trading."
    evidence = macquarie_sales_trading_evidence("<p>" + clause + "</p>")
    assert len(evidence) == 1
    assert evidence[0].minimum_years == 5
    assert evidence[0].excerpt in clause
    assert "5 years" in evidence[0].excerpt


@pytest.mark.parametrize(
    "html",
    [
        pytest.param(MACQUARIE_PARAGRAPH, id="plain-text-cannot-prove-paragraph-boundary"),
        pytest.param(
            "<p>Our team has 5 years of experience in sales trading.</p>",
            id="corporate-history",
        ),
        pytest.param(
            "<p>Contract duration: 5 years. Experience in sales trading is useful.</p>",
            id="contract-duration",
        ),
        pytest.param(
            "<p>Ideally 5 years of experience in sales trading.</p>",
            id="leading-preference",
        ),
        pytest.param(
            "<p>5 years of experience in sales trading preferred.</p>",
            id="attached-preference",
        ),
        pytest.param(
            "<p>5 years of experience in sales trading is not required.</p>",
            id="negation",
        ),
        pytest.param(
            "<p>Up to 5 years of experience in sales trading.</p>",
            id="maximum-duration",
        ),
        pytest.param(
            "<p>A doctorate or 5 years of experience in sales trading.</p>",
            id="leading-academic-alternative",
        ),
        pytest.param(
            "<p>5 years of experience in sales trading or a doctorate.</p>",
            id="trailing-academic-alternative",
        ),
        pytest.param(
            "<p>5-2 years of experience in sales trading.</p>",
            id="inverted-range",
        ),
        pytest.param(
            "<p>2-5 years of experience in sales trading.</p>",
            id="range-outside-new-rule",
        ),
        pytest.param(
            "<p>1.5 years of experience in sales trading.</p>",
            id="decimal",
        ),
        pytest.param(
            "<p>-5 years of experience in sales trading.</p>",
            id="negative",
        ),
        pytest.param(
            "<p>100 years of experience in sales trading.</p>",
            id="outside-model-bounds",
        ),
        pytest.param(
            "<p>5 years of experience in accounting.</p>",
            id="another-professional-domain",
        ),
    ],
)
def test_macquarie_uncertain_context_does_not_supply_a_professional_minimum(html):
    assert macquarie_sales_trading_evidence(html) == []


@pytest.mark.parametrize(
    ("method", "origin", "kind"),
    [
        ("ca_cib_experience_level", "description", "professional"),
        ("ca_cib_experience_level", "employer_field", "industry_or_academia"),
        ("ca_cib_experience_level", "employer_field", "unspecified"),
        ("macquarie_sales_trading_experience", "employer_field", "professional"),
        ("macquarie_sales_trading_experience", "description", "industry_or_academia"),
        ("jump_coding_track_record", "employer_field", "professional"),
    ],
)
def test_evidence_cannot_mislabel_the_origin_or_kind_of_an_extraction(method, origin, kind):
    with pytest.raises(ValidationError):
        ExperienceEvidence(
            minimum_years=5,
            method=method,
            origin=origin,
            kind=kind,
            excerpt="Published evidence",
        )
