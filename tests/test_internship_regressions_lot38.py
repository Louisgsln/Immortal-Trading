"""Independent internship regressions from the lot 38 read-only corpus audit."""

import pytest

from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job

DESCRIPTION_EXCLUSION = "description explicitly identifies a Jane Street internship"


def _job(description, **changes):
    values = {
        "company": "Jane Street",
        "title": "Quantitative Trader",
        "description": description,
        "source": "jane_street",
        "source_type": "official",
        "apply_url": "https://example.org/jobs/independent-internship-regression",
        "employment_type": None,
    }
    values.update(changes)
    return normalize(RawJob(**values))


@pytest.mark.parametrize(
    "description",
    [
        pytest.param(
            "As an intern, you'll be paired with full-time employees who act as mentors, "
            "collaborating with you on real-world projects we actually need done.",
            id="fundamental-146c550f-generic-role",
        ),
        pytest.param(
            "As a Fundamental Analyst Intern, you'll join our Equities and Commodities "
            "Fundamental teams to learn how we integrate in-depth research with the "
            "firm's core quantitative strategies.",
            id="fundamental-146c550f-named-role",
        ),
        pytest.param(
            "During the internship, your work is reinforced with intensive classes, "
            "workshops, and team-based mock trading sessions.",
            id="quant-trader-0ac3bc87-current-work",
        ),
        pytest.param(
            "You'll spend the bulk of your internship working closely with full-time "
            "researchers on projects drawn from their own work.",
            id="quant-researcher-52683156-future-own-internship",
        ),
        pytest.param(
            "Over the course of your internship, you will explore ways to approach "
            "and solve exciting problems within your field of interest through fun "
            "and challenging classes, interactive sessions, and group discussions — "
            "and then you will have the chance to put those lessons to practical use.",
            id="linux-0c2b717c-future-own-internship",
        ),
        pytest.param(
            "During the internship, you will work in collaboration with your mentors "
            "on one project for about 10-12 weeks.",
            id="tools-compilers-0a292fa8-future-work",
        ),
    ],
)
def test_exact_description_evidence_excludes_without_changing_source_fields(config, description):
    item = _job(description)
    original = item.model_dump(mode="json")
    result = score_job(item, config.keywords)
    assert result.score_breakdown.total == 0
    assert DESCRIPTION_EXCLUSION in result.score_breakdown.exclusions
    for key in (
        "description",
        "description_text",
        "employment_type",
        "title",
        "source",
        "source_type",
        "apply_url",
    ):
        assert result.model_dump(mode="json")[key] == original[key]


@pytest.mark.parametrize(
    "description",
    [
        pytest.param(
            "Since our inception as a skunkworks intern project in late 2015, we've "
            "grown into a dynamic and seasoned team of high performing players "
            "across a range of functions.",
            id="jump-1a63f592-business-history",
        ),
        pytest.param(
            "Knowledge of sales, trading, and market risk concepts, gained through "
            "academic studies, internships, or relevant experience.",
            id="deutsche-f3f5031e-prior-experience",
        ),
        pytest.param(
            "We are looking for an experienced Campus Recruiter to help us find and "
            "hire outstanding interns to join Jane Street.",
            id="jane-street-1d21c2bb-recruiting-others",
        ),
        pytest.param(
            "You will mentor interns and design their internship projects. "
            "During the internship, your interns will learn pricing models.",
            id="mentoring-other-candidates",
        ),
        pytest.param(
            "If you join us as an intern, you will work on pricing models. "
            "This vacancy is for a permanent trader.",
            id="conditional-other-programme",
        ),
        pytest.param(
            "This role is not an internship. You will work as a full-time trader.",
            id="explicit-negation",
        ),
        pytest.param(
            "You will not work as an intern, you will join our permanent trading team.",
            id="negated-role-with-you",
        ),
        pytest.param(
            'A former colleague wrote: "As an intern, you will learn from mentors." '
            "This vacancy is for a permanent trader.",
            id="quoted-other-role",
        ),
        pytest.param(
            '"During the internship, you will learn trading" is an excerpt from our '
            "student brochure, not this permanent vacancy.",
            id="quoted-other-programme-at-start",
        ),
        pytest.param(
            "As an intern, you worked on pricing models before graduation. "
            "Now you will join as a full-time trader.",
            id="former-role-past-tense",
        ),
        pytest.param(
            "During your previous internship, you learned how to price options.",
            id="explicit-previous-internship",
        ),
        pytest.param(
            "Citi is looking for intern analysts to join our Markets team in London. "
            "The Quantitative Analysis associate program offers opportunities in "
            "the Quantitative Analysis group. Time Type: Full time.",
            id="citi-0843609f-contradictory-programme",
        ),
        pytest.param(
            "Susquehanna is seeking talented graduates to join their growing Dublin "
            "office in August 2027. Throughout the summer, interns enjoy weekly "
            "social events. For those joining us from outside Dublin, we also "
            "provide accommodation for the duration of the internship.",
            id="susquehanna-130ff023-benefits-boilerplate",
        ),
        pytest.param(
            "Learn more about Jane Street's internship program here. "
            "Our full-time traders design market making strategies.",
            id="link-to-another-programme",
        ),
    ],
)
def test_other_people_past_conditional_negated_or_quoted_roles_keep_ranking(config, description):
    result = score_job(_job(description), config.keywords)
    assert result.score_breakdown.exclusions == []
    assert result.score_breakdown.total > 0


def test_stage_exclusion_remains_independent_of_research_analyst_exclusion(config):
    item = _job(
        "As a Fundamental Analyst Intern, you'll join our Equities and Commodities "
        "Fundamental teams to learn how we integrate in-depth research with the "
        "firm's core quantitative strategies.",
        title="Fundamental Research Analyst",
    )
    result = score_job(item, config.keywords)
    assert "research analyst" in result.score_breakdown.exclusions
    assert DESCRIPTION_EXCLUSION in result.score_breakdown.exclusions
    assert result.score_breakdown.total == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"company": "Another Firm"},
        {"source": "unverified_board"},
        {"source_type": "board"},
    ],
)
def test_company_specific_evidence_does_not_expand_to_other_sources(config, changes):
    item = _job("As an intern, you will work alongside mentors.", **changes)
    result = score_job(item, config.keywords)
    assert DESCRIPTION_EXCLUSION not in result.score_breakdown.exclusions
    assert result.score_breakdown.total > 0
