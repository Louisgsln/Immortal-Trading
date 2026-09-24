import pytest

from trading_radar.degree_experience import degree_experience_years
from trading_radar.experience import experience_requirement
from trading_radar.scoring import required_experience_years, score_job

DB_WRITTEN = (
    "Requires a Master’s degree in Finance, Financial Engineering, or a related field "
    "or equivalent and three (3) years of experience developing hedging strategies "
    "and managing risk for highly complex, non linear derivative portfolios; "
    "designing and validating financial models in Excel."
)
DB_RANGE = (
    "Your skills and experience: To be successful in this role you will have: "
    "1-4 years of prior work experience in Asia Emerging Markets FX trading within "
    "a Tier One financial institution Knowledge of quantitative trading techniques "
    "for FX or Macro across both developed and emerging markets"
)


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Preferred qualifications: Knowledge of pricing. Requires a degree and three (3) years of experience",
            [],
        ),
        ("Optional requirements:\nSQL\nRequires a degree and three (3) years of experience", []),
        (DB_WRITTEN, [3]),
        (DB_RANGE, [1]),
        ("Requires a bachelor's degree and zero (0) years of experience", [0]),
        ("Must have a degree in finance and five (5) years of relevant work experience", [5]),
        ("REQUIRES A MASTER'S DEGREE AND THREE (3) YEARS OF EXPERIENCE", [3]),
        ("Qualifications: 0–2 years of prior work experience", [0]),
        ("Candidates with 2—5 years of prior experience", [2]),
        (
            "Qualifications: 1-4 years of prior work experience Strong communication skills preferred",
            [1],
        ),
    ],
)
def test_explicit_written_and_prior_requirements(text, expected):
    assert required_experience_years(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        DB_WRITTEN.replace("three (3)", "three (4)"),
        DB_WRITTEN.replace("three (3)", "thirty (3)"),
        DB_WRITTEN.replace("three (3)", "three (103)"),
        DB_WRITTEN.replace("Requires", "Does not require"),
        DB_WRITTEN.replace("Requires", "Preferred: requires"),
        DB_WRITTEN.replace("Requires", "Our company has"),
        DB_WRITTEN.replace("Requires", "She holds"),
        DB_WRITTEN.replace("and three", "or three"),
        DB_WRITTEN.replace("and three", "and up to three"),
        DB_WRITTEN.replace("and three", "and at most three"),
        "Requires a degree and three (3) years of experience preferred",
        "Requires a degree and three (3) years of experience is not needed",
        "Requires a degree and three (3) years of experience or a doctorate",
        "Requires a degree and three (3) years of experience; or a doctorate",
        "Requires a degree and three (3) years of experience may be waived",
        "Requires a degree and three (3) years of experience or two (2) years with a master's degree",
        "Requires a degree and three (3) years of experience; alternatively a diploma",
        "Requires a degree and three (3) years of a contract",
        "Requires a degree and three (3) years in university",
        "Requires a degree and three (3) years of experience or equivalent work experience",
        "A degree and three (3) years of experience",  # no explicit requirement verb
        "Requires a degree\nand three (3) years of experience",
        "Qualifications: 1-4 years of prior work experience preferred",
        "Preferred Qualifications: 1-4 years of prior work experience",
        "Qualifications: 1-4 years of prior work experience is not needed",
        "Qualifications: without 1-4 years of prior work experience",
        "Qualifications: at most 1-4 years of prior work experience",
        "Qualifications: 4-1 years of prior work experience",
        "Qualifications: 101-104 years of prior work experience",
        "Qualifications: 1-4 years of prior work experience or a doctorate",
        "Qualifications: a degree or 1-4 years of prior work experience",
        "Our team has 1-4 years of prior work experience",
    ],
)
def test_preferences_alternatives_and_nonrequirements_stay_unknown(text):
    assert required_experience_years(text) == []


def test_existing_degree_plus_rule_is_unchanged():
    assert degree_experience_years("Requires a degree plus 3 years of experience") == [3]


def test_required_section_resets_prior_optional_scope():
    text = "Preferred qualifications: SQL. Required qualifications: Requires a degree and three (3) years of experience"
    assert required_experience_years(text) == [3]


@pytest.mark.parametrize("description,minimum,junior", [(DB_WRITTEN, 3, 0), (DB_RANGE, 1, 20)])
def test_experience_and_score_use_the_same_requirement(job, config, description, minimum, junior):
    job.description_text = description
    before = job.model_dump()
    assert experience_requirement(job)["minimum_years"] == minimum
    assert job.model_dump() == before
    scored = score_job(job.model_copy(deep=True), config.keywords)
    assert scored.score_breakdown.junior == junior
    assert scored.description_text == description
