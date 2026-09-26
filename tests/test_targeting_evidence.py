import pytest

from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


def scored(config, source, company, title, description):
    return score_job(
        normalize(
            RawJob(
                source=source,
                source_type="official",
                company=company,
                title=title,
                description=description,
                apply_url="https://example.test/job",
            )
        ),
        config.keywords,
    )


JUMP = "What You'll Do: Collaborate with quantitative traders on ETF pricing and trading strategy. Determine fair value and generate trade ideas. Skills You’ll Need: 3–6 years in buy/sell-side research, prop trading, ETF/index research, or corporate actions analysis."
JANE = "About the Position: Build models, strategies and systems that price and trade financial instruments. Run trading strategies. About You: Python skills."
DRW = "What you would do: Build and own the pricing framework. Produce reservation bids and offers. Work directly with trading, risk. What we are looking for: PhD or MSc."


@pytest.mark.parametrize(
    "source,company,title,body",
    [
        ("jane_street", "Jane Street", "Quantitative Researcher", JANE),
        ("drw", "DRW", "Quant Researcher - Compute Markets", DRW),
        ("jump_trading", "Jump Trading", "Quantamental Research Analyst | Trading Team", JUMP),
    ],
)
def test_audited_research_has_trading_evidence_without_company_boilerplate(
    config, source, company, title, body
):
    current = scored(config, source, company, title, body)
    assert "QUANT_RESEARCH" in current.desk
    assert "research analyst" not in current.score_breakdown.exclusions
    assert current.score_breakdown.front_office == 15
    assert "QUANT_RESEARCH" not in scored(config, source, "Unrelated employer", title, body).desk
    assert (
        "QUANT_RESEARCH"
        not in scored(
            config,
            source,
            company,
            title,
            body.replace("What you would do", "About us")
            .replace("What You'll Do", "About us")
            .replace("About the Position", "About us"),
        ).desk
    )


def test_research_exception_preserves_experience_and_contract_exclusions(config):
    current = scored(
        config, "jump_trading", "Jump Trading", "Quantamental Research Analyst | Trading Team", JUMP
    )
    assert current.score_breakdown.junior == 0
    assert current.score_breakdown.total < 70
    senior = scored(
        config,
        "jump_trading",
        "Jump Trading",
        "Quantamental Research Analyst | Trading Team",
        JUMP.replace("3–6", "5–8"),
    )
    assert senior.score_breakdown.total == 0
    assert any("5 years" in reason for reason in senior.score_breakdown.exclusions)
    internship = scored(
        config,
        "jane_street",
        "Jane Street",
        "Quantitative Researcher",
        JANE.replace(
            "About the Position:", "About the Position: As an intern, you will build tools."
        ),
    )
    assert internship.score_breakdown.total == 0
    unrelated = scored(
        config,
        "jump_trading",
        "Jump Trading",
        "Research Analyst",
        "What You’ll Do: publish reports. Skills You’ll Need: Finance.",
    )
    assert "research analyst" in unrelated.score_breakdown.exclusions


def test_explicit_drw_junior_description_requires_actual_trading_responsibilities(config):
    body = "As a Junior Trader, you will operate trading strategies. Responsibilities: Manually trade to reduce risk exposure when necessary. Adjust system parameters dynamically based on market conditions. Required Experience: Python. Nice to Have: Prior trader experience preferred."
    current = scored(config, "drw", "DRW", "Trader", body)
    assert current.seniority == "junior" and current.score_breakdown.junior == 20
    assert (
        scored(
            config,
            "drw",
            "DRW",
            "Trader",
            body.replace("As a Junior Trader, you will", "Work with a Junior Trader to"),
        ).seniority
        == "unknown"
    )
    assert (
        scored(
            config,
            "drw",
            "DRW",
            "Trader",
            body.replace(
                "Manually trade to reduce risk exposure when necessary", "Maintain infrastructure"
            ),
        ).seniority
        == "unknown"
    )
    assert scored(config, "drw", "DRW", "Associate Trader", body).score_breakdown.total == 0


@pytest.mark.parametrize(
    "title",
    [
        "HR Partner",
        "HR Generalist",
        "Human Resources Analyst",
        "Trading Assistant (Working Student)",
    ],
)
def test_non_target_functions_stay_excluded(config, title):
    assert scored(
        config, "jane_street", "Jane Street", title, "We are a trading firm."
    ).score_breakdown.exclusions
