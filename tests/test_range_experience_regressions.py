"""Independent corpus regressions for experience ranges, without a live database."""

import pytest

from trading_radar.drw_campus import drw_campus_junior
from trading_radar.experience import experience_requirement
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import required_experience_years, score_job


@pytest.mark.parametrize(
    ("description", "minimum"),
    [
        pytest.param(
            "Qualifications: 6-10 years of experience in a related role Advance statistics "
            "and data analysis background, with modelling capabilities, and spreadsheet "
            "oversight greatly preferred Proven success with a programing background "
            "in one or more programming languages, including: Q/KDB, Python, R Demonstrated "
            "ability to conduct own research, evaluate proof of concepts / prototypes, "
            "articulate ideas and deliver presentations Consistently demonstrates clear "
            "and concise written and verbal communication Attention to Detail and Accuracy "
            "Proven ability to manage to deadlines Education: Bachelor’s degree/University "
            "degree or equivalent experience Master’s degree preferred",
            6,
            id="citi-markets-analyst-d7e09926",
        ),
        pytest.param(
            "Qualifications: 6-12 years structuring experience from a financial institution.",
            6,
            id="citi-corporate-structurer-726eed3f",
        ),
        pytest.param(
            "Qualifications: 6-10 years of experience in a financial services role "
            "Communications or marketing experience preferred Demonstrated working "
            "knowledge of financial services industry Consistently demonstrates clear "
            "and concise written and verbal communication skills Education: Bachelor’s "
            "Degree/University degree or equivalent experience Master’s degree preferred",
            6,
            id="citi-business-execution-29fac7f5",
        ),
        pytest.param(
            "About You 3-6 years of experience in exotic options trading. "
            "Strong quantitative skills in pricing complex derivatives.",
            3,
            id="jane-street-exotic-options-0187a34e",
        ),
        pytest.param(
            "Qualifications Possess 3-7 years of experience in server-side Core Java "
            "and multi-threading.",
            3,
            id="citi-etrading-java-44a344f0",
        ),
        pytest.param(
            "QUALIFICATIONS: Must Have: 1-3 years relevant experience within MARK; "
            "sales or trading functions preferred.",
            1,
            id="sg-junior-fx-em-9f084f59",
        ),
        pytest.param(
            "What we’re looking for 1–2 years of experience in trading, quantitative "
            "analysis, research, or a related role.",
            1,
            id="drw-quantitative-trading-analyst-a456b41d",
        ),
        pytest.param(
            "Qualifications: A degree, or equivalent experience. 5-7 years of work experience.",
            5,
            id="independent-experience-after-education-alternative",
        ),
    ],
)
def test_corpus_ranges_reach_ranking_and_read_only_dashboard(job, config, description, minimum):
    assert required_experience_years(description) == [minimum]
    item = job.model_copy(
        deep=True,
        update={"description_text": description, "minimum_experience_years": None},
    )
    item = score_job(item, config.keywords)
    score = item.score_breakdown
    assert score.junior == (0 if minimum > 2 else 20)
    assert ("requires at least 5 years of experience" in score.exclusions) == (minimum >= 5)
    if minimum >= 5:
        assert score.total == 0
    else:
        assert score.total > 0
    before = item.model_dump(mode="json")
    assert experience_requirement(item) == {
        "minimum_years": minimum,
        "category": "over_2" if minimum > 2 else "up_to_2",
    }
    assert item.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "description",
    [
        pytest.param(
            "Strong analytical and problem solving skills. "
            "1 - 5 years of work experience is preferable. "
            "Prior experience in Finance industry is preferable.",
            id="goldman-trading-desk-strategist-18287b76",
        ),
        pytest.param(
            "Recommended Qualifications: 3-7 years of experience in a related role. "
            "Knowledge of respective products and clients.",
            id="citi-fx-options-7d70d78e",
        ),
        pytest.param(
            "WHO YOU ARE: Typically 3-4 years of options trading experience at a "
            "proprietary trading firm, market maker or bank.",
            id="optiver-digital-assets-25012ba7",
        ),
        pytest.param(
            "Candidates without 5-7 years of experience are welcome.",
            id="candidates-without-experience-welcome",
        ),
        pytest.param(
            "No need for 5-7 years of experience.",
            id="experience-explicitly-not-needed",
        ),
    ],
)
def test_corpus_preferences_and_typical_profiles_do_not_disqualify(job, config, description):
    assert required_experience_years(description) == []
    item = job.model_copy(
        deep=True,
        update={"description_text": description, "minimum_experience_years": None},
    )
    item = score_job(item, config.keywords)
    assert item.score_breakdown.junior == 20
    assert item.score_breakdown.total > 0
    assert "requires at least 5 years of experience" not in item.score_breakdown.exclusions
    assert experience_requirement(item) == {"minimum_years": None, "category": "unspecified"}


@pytest.mark.parametrize(
    "description",
    [
        "Qualifications: Bachelor's degree or 6-10 years of trading experience.",
        "Bachelor's degree plus 6-10 years of experience, or a master's degree "
        "with no prior experience.",
        "Our company has 6-10 years of experience in global markets.",
        "The team brings 6-10 years of trading experience.",
        "Our firm offers 6-10 years of experience in market making.",
    ],
)
def test_alternatives_and_company_history_do_not_become_candidate_minima(job, config, description):
    assert required_experience_years(description) == []
    item = job.model_copy(
        deep=True,
        update={"description_text": description, "minimum_experience_years": None},
    )
    item = score_job(item, config.keywords)
    assert item.score_breakdown.junior == 20
    assert "requires at least 5 years of experience" not in item.score_breakdown.exclusions
    assert experience_requirement(item) == {"minimum_years": None, "category": "unspecified"}


def test_floor_trader_campus_degree_evidence_keeps_82_without_numeric_minimum(config):
    qualification = (
        "A bachelor's degree in Computer Science and have an expected graduation date "
        "between December 2026 and June 2027."
    )
    description = (
        qualification + " Prior trading or financial-markets experience is helpful "
        "but not required. Proficiency in Python is a plus."
    )
    assert drw_campus_junior(
        "Floor Trader",
        "<h2>What you bring to the team</h2><p>" + qualification + "</p>",
        {"Website Job Category Filter": ["Campus"], "Employment Type": "Full-time"},
    )
    item = score_job(
        normalize(
            RawJob(
                company="DRW",
                source="drw",
                source_type="official",
                title="Floor Trader",
                description=description,
                apply_url="https://example.org/jobs/floor-trader",
                seniority_hint="junior",
                employment_type="Full-time",
                expected_start_date="Summer 2027",
            )
        ),
        config.keywords,
    )
    assert item.score_breakdown.total == 82
    assert item.score_breakdown.junior == 20
    assert item.score_breakdown.exclusions == []
    assert experience_requirement(item) == {"minimum_years": None, "category": "unspecified"}
