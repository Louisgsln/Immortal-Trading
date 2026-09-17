import pytest

from trading_radar.normalizer import normalize
from trading_radar.range_experience import plain_range_experience_years
from trading_radar.scoring import required_experience_years, score_job


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Qualifications: 6-10 years of experience in a related role", [6]),
        ("Qualifications: 6-12 years structuring experience from a financial institution", [6]),
        ("About You 3-6 years of experience in exotic options trading", [3]),
        ("Qualifications Possess 3-7 years of experience in server-side Core Java", [3]),
        ("1-3 years relevant experience within MARK; sales or trading functions preferred", [1]),
        ("What we're looking for 1–2 years of experience in trading", [1]),
        ("Who you are Have 2—5 years of experience trading Index Derivatives", [2]),
        ("Your skills and experience: 0–2 years of financial markets experience", [0]),
        ("3-5 years experience", [3]),
        ("You have 3-5 years experience", [3]),
        ("Candidates with 3-5 years of related securities financing experience", [3]),
        ("Qualifications\n6-10 years of experience\nExcellent communication", [6]),
        ("Qualifications: Degree required. 3-5 years experience", [3]),
        ("Qualifications: A degree, or equivalent experience. 5-7 years of work experience", [5]),
        ("Qualifications: 3-5 years experience. 3-5 years relevant experience", [3]),
        ("Qualifications: 2-4 years experience; 3-5 years trading experience", [2, 3]),
        (
            "Qualifications: 6-10 years of experience in a related role "
            "Advance statistics and data analysis background greatly preferred",
            [6],
        ),
        (
            "Qualifications: 6-10 years of experience in a financial services role "
            "Communications or marketing experience preferred",
            [6],
        ),
        ("Recommended Qualifications: SQL. Required Qualifications: 3-5 years experience", [3]),
    ],
)
def test_plain_ranges_supply_lower_bound(text, expected):
    assert plain_range_experience_years(text) == expected
    assert required_experience_years(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Recommended Qualifications: 3-7 years of experience in a related role",
        "Preferred Qualifications: SQL. 3-7 years experience",
        "Preferred Qualifications:\nSQL\n3-7 years experience",
        "Recommended Qualifications SQL programming skills 3-7 years experience",
        "Qualifications: 1 - 5 years of work experience is preferable",
        "Qualifications: Ideally 3-5 years experience",
        "WHO YOU ARE: Typically 3-4 years of options trading experience",
        "Qualifications: Usually 3-5 years experience",
        "Qualifications: Approximately 3-5 years experience",
        "Qualifications: 3-5 years experience would be desirable",
        "Qualifications: 3-5 years experience in trading is preferred",
        "Qualifications: 3-5 years experience is not mandatory",
        "Qualifications: up to 3-5 years experience",
        "Qualifications: less than 3-5 years experience",
        "Qualifications: at most 3-5 years experience",
        "Qualifications: no more than 3-5 years experience",
        "Qualifications: You must not have 5-7 years of experience",
        "Qualifications: Candidates without 5-7 years of experience are welcome",
        "Qualifications: No need for 5-7 years of experience",
        "Qualifications: You do not need 5-7 years of experience",
        "About us: Our firm has 3-5 years experience",
        "Qualifications: Our company has 3-5 years experience",
        "Qualifications: We have 3-5 years experience",
        "About us: 3-5 years experience in trading",
        "Qualifications: She brings 3-5 years experience",
        "Qualifications: A degree or 3-5 years experience",
        "Qualifications: 3-5 years experience or a master's degree",
        "Qualifications: 3-5 years experience; or a degree",
        "Qualifications: 3-5 years experience may be waived",
        "Qualifications: 5-3 years experience",
        "Qualifications: 103-105 years experience",
        "Qualifications: 1.3-5 years experience",
        "Qualifications: -3-5 years experience",
        "Qualifications: x3-5 years experience",
        "Qualifications: 3-5.5 years experience",
        "Qualifications: 3-5+ years experience",
        "Qualifications: 3+ years experience",
        "Qualifications: 3 years experience",
        "Qualifications: 3-5 years in trading",
        "Qualifications: 3-5 years of company history",
        "Qualifications: 3-5 years. Experience in trading",
        "Qualifications: 3-5 years\nexperience in trading",
    ],
)
def test_ambiguous_optional_and_out_of_scope_ranges_are_ignored(text):
    assert plain_range_experience_years(text) == []


@pytest.mark.parametrize(
    ("years", "junior", "excluded"), [("1-3", 20, False), ("3-6", 0, False), ("6-10", 0, True)]
)
def test_new_range_requirement_reaches_scoring(raw, config, years, junior, excluded):
    raw.title = "Trading Analyst"
    raw.description = f"Qualifications: {years} years of experience in trading. FX Python SQL."
    scored = score_job(normalize(raw), config.keywords)
    assert scored.score_breakdown.junior == junior
    assert (
        "requires at least 5 years of experience" in scored.score_breakdown.exclusions
    ) is excluded


def test_existing_plus_and_degree_patterns_keep_their_results():
    assert required_experience_years("3-6+ years of experience") == [3]
    assert required_experience_years("Degree plus 7 years experience") == [7]
    assert required_experience_years("Minimum 4 years experience") == [4]
