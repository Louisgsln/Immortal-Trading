import html

import pytest

from trading_radar.drw_campus import drw_campus_junior

FIELDS = {"Website Job Category Filter": ["Campus"], "Employment Type": "Full-time"}
REQUIREMENT = (
    "A bachelor’s in economics, finance, mathematics, statistics, computer science "
    "or any related field and have an expected graduation date between December 2026 and June 2027"
)


def description(requirement: str = REQUIREMENT) -> str:
    return (
        "<p>Develop trading decisions alongside traders.</p>"
        "<p><strong>What you bring to the team…</strong></p>"
        f"<ul><li>{requirement}</li><li>Prior trading experience is helpful but not required</li></ul>"
        "<p><strong>DRW </strong>is a diversified trading firm.</p>"
    )


@pytest.mark.parametrize("encoded", [False, True])
def test_audited_expected_graduation_in_candidate_requirement(encoded: bool) -> None:
    content = description()
    if encoded:
        content = html.escape(content)
    assert drw_campus_junior("Floor Trader", content, FIELDS)


def test_synthetic_paraphrase_does_not_bind_title_or_year() -> None:
    content = description(
        "A degree in physics with an expected graduation date between January 2031 and August 2032"
    )
    assert drw_campus_junior("Options Trader", content, FIELDS)


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"Employment Type": "Full-time"},
        FIELDS | {"Website Job Category Filter": None},
        FIELDS | {"Website Job Category Filter": "Campus"},
        FIELDS | {"Website Job Category Filter": []},
        FIELDS | {"Website Job Category Filter": ["Experienced"]},
        FIELDS | {"Website Job Category Filter": ["Campus", "Experienced"]},
        FIELDS | {"Website Job Category Filter": ["campus"]},
        FIELDS | {"Website Job Category Filter": {"name": "Campus"}},
        FIELDS | {"Employment Type": None},
        FIELDS | {"Employment Type": ["Full-time"]},
        FIELDS | {"Employment Type": "Regular"},
        FIELDS | {"Employment Type": "Intern"},
        FIELDS | {"Employment Type": "Apprenticeship"},
    ],
)
def test_missing_invalid_or_conflicting_metadata(fields: dict[str, object]) -> None:
    assert not drw_campus_junior("Trader", description(), fields)


@pytest.mark.parametrize("title", ["Trader Intern", "Trading Internship", "Apprentice Trader"])
def test_full_time_is_not_enough_for_intern_title(title: str) -> None:
    assert not drw_campus_junior(title, description(), FIELDS)


@pytest.mark.parametrize(
    "requirement",
    [
        "A bachelor's degree in finance",
        "A bachelor's degree and a graduation date between December 2026 and June 2027",
        "A bachelor's degree completed in 2020",
        "A bachelor's degree and had an expected graduation date between December 2026 and June 2027",
        "A bachelor's degree already awarded with an expected graduation date between December 2026 and June 2027",
        "Our employees have an expected graduation date between December 2026 and June 2027",
        "Our founder holds " + REQUIREMENT,
        REQUIREMENT + " is optional",
        REQUIREMENT + " is preferred",
        REQUIREMENT + " would be desirable",
        REQUIREMENT + " is helpful",
        REQUIREMENT + " is not essential",
        REQUIREMENT.replace("expected graduation date", "previous graduation date"),
        REQUIREMENT.replace(" and have an expected", ". Have an expected"),
        REQUIREMENT.replace(" and have an expected", "; have an expected"),
        REQUIREMENT.replace(" and have an expected", "\nhave an expected"),
        REQUIREMENT.replace(" and have an expected", "</li><li>Have an expected"),
        REQUIREMENT.replace("December 2026", "sometime"),
    ],
)
def test_no_generic_past_optional_or_disconnected_graduation(requirement: str) -> None:
    assert not drw_campus_junior("Trader", description(requirement), FIELDS)


@pytest.mark.parametrize(
    "content",
    [
        "<p>" + REQUIREMENT + "</p>",
        description().replace("What you bring to the team", "Our company"),
        description() + "<p>What you bring to the team</p>",
        description("Excellent communication") + "<p>" + REQUIREMENT + "</p>",
        description().replace(
            "Develop trading decisions", "During this internship develop trading decisions"
        ),
        description().replace(
            "Prior trading experience", "This apprenticeship requires trading experience"
        ),
        description().replace(
            "<p><strong>DRW",
            "<h2>What to expect during the internship</h2><p><strong>DRW",
        ),
    ],
)
def test_scope_and_placement_evidence(content: str) -> None:
    assert not drw_campus_junior("Trader", content, FIELDS)


def test_generic_company_internship_program_does_not_describe_the_role() -> None:
    assert drw_campus_junior("Trader", description() + "<p>We also offer internships.</p>", FIELDS)
