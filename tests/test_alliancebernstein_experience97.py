"""Do not alert a junior candidate on the audited 5-7yrs credit-trader role."""

import pytest

from trading_radar.config import load_config
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.workday import workday_minimum_experience

INTRO = "The successful candidate is likely to have the following qualifications:"
BULLET = (
    "5-7yrs experience in a credit trading role, with a preference to IG or HY US markets exposure."
)


def document(bullet=BULLET, intro=INTRO):
    return f"<p>What We’re Looking For:</p><p>{intro}</p><ul><li><p>{bullet}</p></li></ul>"


def test_audited_ab_experience_excludes_the_role_without_changing_general_scores():
    description = document()
    minimum = workday_minimum_experience("alliancebernstein", "AllianceBernstein", description)
    assert minimum == 5
    job = normalize(
        RawJob(
            source="alliancebernstein",
            source_type="official",
            company="AllianceBernstein",
            external_id="123",
            title="Credit Trader - Investment Grade",
            description=description,
            apply_url="https://abglobal.wd1.myworkdayjobs.com/alliancebernsteincareers/job/123",
            minimum_experience_years=minimum,
        )
    )
    scored = score_job(job, load_config().keywords)
    assert scored.score_breakdown.total == 0
    assert "requires at least 5 years of experience" in scored.score_breakdown.exclusions


@pytest.mark.parametrize(
    "bullet",
    [
        "Preferably " + BULLET,
        "Up to " + BULLET,
        "Our team has " + BULLET,
        BULLET + " Equivalent education is accepted instead.",
        BULLET.replace("5-7", "7-5"),
        BULLET.replace("5-7", "1.5-7"),
        BULLET.replace("5-7yrs", "No"),
        BULLET.replace("experience", "preferred experience"),
        BULLET.replace("experience", "academic experience"),
    ],
)
def test_optional_alternative_or_nonprofessional_claims_do_not_supply_a_minimum(bullet):
    assert (
        workday_minimum_experience("alliancebernstein", "AllianceBernstein", document(bullet))
        is None
    )


@pytest.mark.parametrize("intro", ["About AB", "Preferred qualifications", "", "Our history"])
def test_exact_candidate_section_required(intro):
    assert (
        workday_minimum_experience("alliancebernstein", "AllianceBernstein", document(intro=intro))
        is None
    )


@pytest.mark.parametrize(
    "source,company", [("other", "AllianceBernstein"), ("alliancebernstein", "Other")]
)
def test_ab_parser_cannot_change_unrelated_employer_requirements(source, company):
    assert workday_minimum_experience(source, company, document()) is None


def test_hidden_bullet_is_not_candidate_evidence():
    html = document().replace("<li>", "<li hidden>")
    assert workday_minimum_experience("alliancebernstein", "AllianceBernstein", html) is None
