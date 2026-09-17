import pytest

from trading_radar.degree_experience import degree_experience_years

SUSQUEHANNA = (
    "What we're looking for Bachelor's degree in Computer Science, Engineering, "
    "Mathematics or related discipline or its foreign equivalent plus 7 years of "
    "progressive experience developing software applications. Relevant technical "
    "experience may substitute for education"
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (SUSQUEHANNA, [7]),
        ("Bachelor's degree plus 7 years of experience.", [7]),
        ("Master’s degree in Finance plus 2 years relevant experience.", [2]),
        ("UNIVERSITY DEGREE PLUS 3 YEARS OF PROFESSIONAL WORK EXPERIENCE", [3]),
        ("Degree in mathematics or physics plus 4 years experience", [4]),
        ("Bachelor's degree or its foreign equivalent plus 7 years experience", [7]),
        ("Degree plus 0 years experience", [0]),
        ("Degree plus 2-5 years experience", [2]),
        ("Degree plus 2–5+ years experience", [2]),
        ("Degree plus 2—5 years experience", [2]),
        ("Degree plus 2+ years experience", [2]),
        ("Degree plus 2 years experience. Degree plus 3 years experience", [2, 3]),
        ("Degree plus 2 years experience; Degree plus 2 years experience", [2]),
        ("Degree plus 2 years experience\nDegree plus 3 years experience", [2, 3]),
        ("Degree preferred. Degree plus 7 years experience", [7]),
        ("Our company requires a bachelor's degree plus 7 years experience", [7]),
        ("Degree plus 7 years experience. Salary plus bonus", [7]),
        ("Degree plus 7 years experience; Master's degree preferred", [7]),
    ],
)
def test_explicit_additive_degree_experience(text: str, expected: list[int]) -> None:
    assert degree_experience_years(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Bachelor's degree or 7 years experience",
        "Bachelor's degree or equivalent experience",
        "Bachelor's degree and 7 years experience",
        "Degree is a plus, 7 years experience",
        "Degree plus salary of 7 years experience",
        "Degree plus 7 years of age",
        "Degree plus 7 years since the company was founded",
        "Degree plus 7 years of company history",
        "Degree plus 7 years of highly specific unrelated trading software experience",
        "Degree and salary plus 7 years experience",
        "Degree and experience plus 7 years experience",
        "Our company has a degree plus 7 years experience",
        "The team brings a degree plus 7 years experience",
        "She holds a degree plus 7 years experience",
        "Preferred qualifications: Bachelor's degree plus 7 years experience",
        "Ideally a degree plus 7 years experience",
        "Degree preferred plus 7 years experience",
        "Degree plus 7 years experience is preferred",
        "Degree plus 7 years experience developing applications would be desirable",
        "Degree plus 7 years experience is not required",
        "Degree plus 7 years experience is not mandatory",
        "Degree plus 7 years experience is an advantage",
        "Degree plus 7 years experience is an asset",
        "Degree plus 7 years experience is desired",
        "Degree plus 7 years experience is a plus",
        "Degree plus 7 years experience or Master's degree plus 2 years experience",
        "Either a degree plus 7 years experience or equivalent experience",
        "Degree plus 7 years experience or 2 years in a related role",
        "Degree plus 7 years experience or no experience with a master's qualification",
        "Degree plus 7 years experience or MSc plus 2 years experience",
        "Bachelor's degree plus 7 years of experience, or MSc with no prior experience.",
        "Bachelor's degree plus 7 years of experience, or an MBA.",
        "Bachelor's degree plus 7 years of experience, or M.Sc. with no prior experience.",
        "Degree plus 7 years experience or a professional credential",
        "MSc or university degree plus 7 years experience",
        "Degree plus 7 years experience alternatively a master's qualification",
        "Degree plus 7 years experience may be waived",
        "Degree plus 7 years experience in lieu of another qualification",
        "Degree plus 7 years experience; or Master's degree plus 2 years experience",
        "Degree plus 7 years experience. Or Master's degree plus 2 years experience",
        "Degree plus 7 years experience\nor Master's degree plus 2 years experience",
        "Degree. Plus 7 years experience",
        "Degree; plus 7 years experience",
        "Degree\nplus 7 years experience",
        "Degree plus 7 years. Experience in trading",
        "Degree plus 7 years; experience in trading",
        "Degree plus 7 years\nexperience in trading",
        "Degree plus 5-2 years experience",
        "Degree plus -7 years experience",
        "Degree plus 7.5 years experience",
        "Degree plus 107 years experience",
        "Degree plus 7 years old",
        "Degree " + "in mathematics " * 20 + "plus 7 years experience",
    ],
)
def test_ambiguous_or_unrelated_degree_statements_are_ignored(text: str) -> None:
    assert degree_experience_years(text) == []
