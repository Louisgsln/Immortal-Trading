import pytest
from pydantic import ValidationError

from trading_radar.greenhouse_filtered import jump_track_record_evidence, jump_track_record_minimum
from trading_radar.models import ExperienceEvidence, RawJob
from trading_radar.normalizer import plain_text

PROOF = "5+ year track record of solving challenging problems through coding"


@pytest.mark.parametrize(
    ("ending", "kind", "minimum"),
    [
        (" with real metrics & impact in industry.", "professional", 5),
        (" with real metrics & impact in industry and/or academia.", "industry_or_academia", None),
        (" in industry or academic research.", "industry_or_academia", None),
        (" with real metrics.", "unspecified", None),
        (" in academia.", "unspecified", None),
        (" using industry-leading tools.", "unspecified", None),
        (".", "unspecified", None),
    ],
)
def test_track_record_kind_separates_achievement_from_professional_years(ending, kind, minimum):
    content = f"<h2>Skills You’ll Need</h2><p>{PROOF}{ending}</p>"
    [evidence] = jump_track_record_evidence(content)
    assert evidence.minimum_years == 5
    assert evidence.kind == kind
    assert evidence.origin == "description"
    assert evidence.method == "jump_coding_track_record"
    assert evidence.excerpt == PROOF + ending
    assert evidence.excerpt in plain_text(content)
    assert jump_track_record_minimum(content) == minimum


@pytest.mark.parametrize("apostrophe", ["'", "’", "\ufffd"])
def test_known_heading_encodings_keep_exact_proof(apostrophe):
    content = f"<h2>Skills You{apostrophe}ll Need</h2><p>{PROOF} in industry &amp; academia.</p>"
    [evidence] = jump_track_record_evidence(content)
    assert evidence.excerpt == PROOF + " in industry & academia."
    assert evidence.kind == "industry_or_academia"


@pytest.mark.parametrize(
    "content",
    [
        PROOF + " in industry.",
        "About us: " + PROOF + " in industry. Skills You'll Need: Python.",
        "Preferred Skills You'll Need: " + PROOF + " in industry.",
        "Skills You'll Need: Python. Nice to Have: " + PROOF + " in industry.",
        "Skills You'll Need: Python. Preferred: " + PROOF + " in industry.",
        "Skills You'll Need: Python. Recommended Qualifications: " + PROOF + " in industry.",
        "Skills You'll Need: " + PROOF + " in industry is preferred.",
        "Skills You'll Need: " + PROOF + " in industry is nice to have.",
        "Skills You'll Need: " + PROOF + " in industry is not required.",
        "Skills You'll Need: " + PROOF + " in industry may be waived.",
        "Skills You'll Need: " + PROOF + " in industry or a master's degree.",
        "Skills You'll Need: " + PROOF + " in industry. Or no experience.",
        "Skills You'll Need: " + PROOF + " in industry; alternatively a PhD.",
        "Skills You'll Need: Our firm has " + PROOF + " in industry.",
        "Skills You'll Need: Ideally " + PROOF + " in industry.",
        "Skills You'll Need: " + PROOF.replace("5+", "1.5+") + " in industry.",
        "Skills You'll Need: " + PROOF.replace("5+", "105+") + " in industry.",
        "Skills You'll Need: " + PROOF.replace("5+", "-5+") + " in industry.",
        "Skills You'll Need: " + PROOF.replace("5+", "2-5+") + " in industry.",
        "Skills You'll Need: " + PROOF.replace("through coding", "in investing") + " in industry.",
        "Skills You'll Need: " + PROOF + " in industry. Skills You'll Need: Python.",
    ],
)
def test_ambiguous_optional_and_unrelated_claims_supply_no_evidence(content):
    assert jump_track_record_evidence(content) == []
    assert jump_track_record_minimum(content) is None


def test_multiple_evidence_items_keep_order_and_only_professional_minimum():
    content = (
        "Skills You'll Need: "
        + PROOF.replace("5+", "2+")
        + " in industry. "
        + PROOF
        + " in industry and/or academia. "
        + PROOF.replace("5+", "3+")
        + " in industry."
    )
    evidence = jump_track_record_evidence(content)
    assert [(item.minimum_years, item.kind) for item in evidence] == [
        (2, "professional"),
        (5, "industry_or_academia"),
        (3, "professional"),
    ]
    assert jump_track_record_minimum(content) == 3


@pytest.mark.parametrize("years", [0, 99])
def test_model_bounds_and_serialization(years):
    evidence = ExperienceEvidence(minimum_years=years, kind="professional", excerpt=PROOF)
    assert ExperienceEvidence.model_validate_json(evidence.model_dump_json()) == evidence


@pytest.mark.parametrize(
    "changes",
    [
        {"minimum_years": -1},
        {"minimum_years": 100},
        {"kind": "unknown"},
        {"origin": "metadata"},
        {"method": "generic"},
    ],
)
def test_model_rejects_invalid_contract(changes):
    value = {"minimum_years": 5, "kind": "professional", "excerpt": PROOF, **changes}
    with pytest.raises(ValidationError):
        ExperienceEvidence.model_validate(value)


def test_old_raw_json_defaults_to_independent_empty_evidence_lists(raw):
    old = raw.model_dump()
    old.pop("experience_evidence")
    one, two = RawJob.model_validate(old), RawJob.model_validate(old)
    assert one.experience_evidence == two.experience_evidence == []
    one.experience_evidence.append(
        ExperienceEvidence(minimum_years=5, kind="unspecified", excerpt=PROOF)
    )
    assert two.experience_evidence == []
