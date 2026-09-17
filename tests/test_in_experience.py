import pytest

from trading_radar.in_experience import candidate_in_experience_years
from trading_radar.normalizer import normalize
from trading_radar.scoring import required_experience_years, score_job


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Skills You’ll Need: 3–6 years in buy/sell-side research, prop trading", [3]),
        ("Skills You'll Need: 3-6 years in buy/sell-side research", [3]),
        ("Who you are: 0–2 years in options trading", [0]),
        ("Who you are: 2—5 years in options trading", [2]),
        ("Qualifications: 0+ years in site reliability", [0]),
        ("Qualifications: 7+ years in FPGA (Verilog/VHDL) or low-latency C++ development", [7]),
        (
            "What You Bring: 3+ years in site reliability, systems engineering, or technical "
            "operations, ideally supporting high-performance or real-time systems",
            [3],
        ),
        ("Qualifications: 3+ years in site reliability, ideally supporting real-time systems", [3]),
        (
            "Who you are: 3+ years in options trading, market making, floor brokerage, "
            "or exchange operations. Preferred: Prior listed options experience",
            [3],
        ),
        (
            "Who you are 3+ years in options trading Preferred: Prior listed options experience",
            [3],
        ),
        ("Preferred qualifications: SQL. Required qualifications: 3+ years in FPGA", [3]),
        ("Qualifications\n3+ years in FPGA\nPreferred: Linux", [3]),
        ("Qualifications: 3+ years in options trading; 4+ years in FPGA", [3, 4]),
        ("Qualifications: 3+ years in options trading. 3+ years in FPGA", [3]),
        ("Qualifications: A degree or equivalent experience. 3+ years in options trading", [3]),
        (
            "Skills You’ll Need: Bachelor’s in Finance, Economics, Mathematics, or a related "
            "quantitative field 3–6 years in buy/sell-side research",
            [3],
        ),
    ],
)
def test_required_professional_activities_supply_lower_bounds(text, expected):
    assert candidate_in_experience_years(text) == expected
    assert required_experience_years(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "3–6 years in buy/sell-side research",
        "Skills You’ll Need: 2+ year track record of solving challenging problems in industry",
        "Skills You’ll Need: 5+ year track record in industry and/or academia",
        "Qualifications: 3 years in options trading",
        "Qualifications: 3+ years in an unknown activity",
        "Preferred qualifications: 3+ years in options trading",
        "Recommended qualifications: SQL. 3+ years in options trading",
        "Qualifications: SQL. Preferred: 3+ years in options trading",
        "Qualifications: SQL. Preferred: Linux\n3+ years in options trading",
        "Qualifications: SQL. About us: 3+ years in options trading",
        "Who you are: SQL. Benefits: 3+ years in options trading",
        "Qualifications: Ideally 3+ years in options trading",
        "Qualifications: around 3+ years in options trading",
        "Qualifications: 3+ years in options trading preferred",
        "Qualifications: 3+ years in options trading is preferable",
        "Qualifications: 3+ years in options trading is not required",
        "Qualifications: 3+ years in options trading is not needed",
        "Qualifications: 3+ years in options trading would be an advantage",
        "Qualifications: 3+ years in site reliability, ideally required",
        "Qualifications: up to 3+ years in options trading",
        "Qualifications: at most 3+ years in options trading",
        "Qualifications: less than 3+ years in options trading",
        "Qualifications: You must not have 3+ years in options trading",
        "Qualifications: You do not need 3+ years in options trading",
        "Qualifications: Candidates without 3+ years in options trading are welcome",
        "Qualifications: No need for 3+ years in options trading",
        "Qualifications: Our company has 3+ years in options trading",
        "Qualifications: The firm has 3+ years in options trading",
        "Qualifications: This team has 3+ years in options trading",
        "Qualifications: We have 3+ years in options trading",
        "Qualifications: Contract duration 3+ years in options trading",
        "Qualifications: You will spend 3-5 years in options trading",
        "Qualifications: extension up to 2 years in total",
        "Qualifications: A degree or 3+ years in options trading",
        "Qualifications: A degree or\n3+ years in options trading",
        "Qualifications: 3+ years in options trading or a PhD",
        "Qualifications: 3+ years in options trading. Or a PhD",
        "Qualifications: 3+ years in options trading or no experience",
        "Qualifications: 3+ years in options trading may be waived",
        "Qualifications: 3+ years in options trading or Master's degree",
        "Qualifications: 6-3 years in options trading",
        "Qualifications: 102+ years in options trading",
        "Qualifications: 1.3+ years in options trading",
        "Qualifications: -3+ years in options trading",
        "Qualifications: x3+ years in options trading",
        "Qualifications: 3-5.5 years in options trading",
        "Qualifications: 3+ years\nin options trading",
        "About You: around 10 years of experience in HR, including 5+ years in an HR role",
    ],
)
def test_preferences_negations_contracts_alternatives_and_unknown_context_are_ignored(text):
    assert candidate_in_experience_years(text) == []


@pytest.mark.parametrize(
    ("years", "junior", "excluded"), [("0-2", 20, False), ("3+", 0, False), ("7+", 0, True)]
)
def test_new_evidence_reaches_scoring_without_changing_source(raw, config, years, junior, excluded):
    raw.title = "Trading Analyst"
    raw.description = f"Qualifications: {years} years in options trading. FX Python."
    job = normalize(raw)
    before = (job.description_text, job.minimum_experience_years, job.title)
    scored = score_job(job, config.keywords)
    assert scored.score_breakdown.junior == junior
    assert (
        "requires at least 5 years of experience" in scored.score_breakdown.exclusions
    ) is excluded
    assert (job.description_text, job.minimum_experience_years, job.title) == before
