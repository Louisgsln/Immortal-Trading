import pytest

from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.targeting import OPERATIONAL_EXCLUSION

CASES = [
    (
        "ubs_professionals",
        "UBS",
        "Trader Assistant",
        "Key responsibilities",
        "Your Career Comeback",
        "Provide operations support to the trading desk, including trade bookings. Ensure data integrity.",
    ),
    (
        "bnp_paribas",
        "BNP Paribas",
        "Institutional Sales Trading Assistant",
        "Your Main Activities Are",
        "Profile and Skills to Success",
        "Help clients finalise their onboarding. Finalising booking of traded deals. Pre-trade checks.",
    ),
    (
        "morgan_stanley",
        "Morgan Stanley",
        "Investment Management - Trading Assistant - Analyst",
        "Primary Responsibilities",
        "Qualifications - External",
        "Perform post-trade functions. Ensure settlement of trades. Confirm and clear derivatives.",
    ),
    (
        "morgan_stanley",
        "Morgan Stanley",
        "Asia Rates Trading Assistant",
        "Primary Responsibilities",
        "Educational background",
        "Trade bookings and amendments; end of day P&L reviews; lifecycle management.",
    ),
    (
        "morgan_stanley",
        "Morgan Stanley",
        "MSIM - Emerging Markets Trading Assistant - Analyst",
        "Key Responsibilities",
        "Candidate Profile",
        "Settlement and reconciliation; account maintenance and onboarding; resolve trading and settlement issues.",
    ),
]


def score(config, source, company, title, body, **kwargs):
    return score_job(
        normalize(
            RawJob(
                source=source,
                source_type="official",
                company=company,
                title=title,
                description=body,
                apply_url="https://example.test/job",
                **kwargs,
            )
        ),
        config.keywords,
    )


@pytest.mark.parametrize("source,company,title,start,end,duties", CASES)
def test_operational_duties_excluded_but_title_alone_is_not(
    config, source, company, title, start, end, duties
):
    body = f"<h2>{start}</h2><p>{duties}</p><h2>{end}</h2><p>Finance and Python.</p>"
    reviewed = score(config, source, company, title, body)
    assert OPERATIONAL_EXCLUSION in reviewed.score_breakdown.exclusions
    assert reviewed.score_breakdown.total == 0
    for changed in [
        body.replace(start, "About the company"),
        body.replace(end, "Unverified boundary"),
        body.replace(duties, "Price options and execute trades."),
        body.replace(f"<p>{duties}</p>", f"<p hidden>{duties}</p>"),
        body + f"<h2>{start}</h2>",
    ]:
        assert (
            OPERATIONAL_EXCLUSION
            not in score(config, source, company, title, changed).score_breakdown.exclusions
        )
    assert (
        OPERATIONAL_EXCLUSION
        not in score(config, "other", company, title, body).score_breakdown.exclusions
    )
    assert (
        OPERATIONAL_EXCLUSION
        not in score(config, source, "Other bank", title, body).score_breakdown.exclusions
    )


def test_real_trading_assistant_manager_is_not_blanket_excluded(config):
    job = score(
        config,
        "bnp_paribas",
        "BNP Paribas",
        "FX Derivatives Trading Assistant Manager",
        "<h2>Main Responsibilities</h2><p>Manage FX risk and price options for clients. Trade bookings and settlement are handled by operations.</p><h2>Requirements</h2><p>Python.</p>",
    )
    assert (
        job.score_breakdown.total >= 55
        and OPERATIONAL_EXCLUSION not in job.score_breakdown.exclusions
    )


def test_middle_officer_is_excluded_without_matching_unrelated_titles(config):
    job = score(
        config,
        "credit_agricole_cib",
        "Crédit Agricole CIB",
        "Middle Officer Support Trading Equity",
        "Trade booking.",
    )
    assert job.score_breakdown.total == 0 and "middle officer" in job.score_breakdown.exclusions
    assert (
        "middle officer"
        not in score(
            config, "test", "Bank", "Equity Trader", "Work with middle officers."
        ).score_breakdown.exclusions
    )


NOMURA_BODY = "<h2>R ole & Responsibilities</h2><p>Hire quants to work on our algorithmic trading platform for eFX. Talented programmers: guiding models through the entire development lifecycle. Develop and manage quantitative analytics.</p><h2>We are committed to providing equal opportunities</h2>"


def test_nomura_support_is_quant_technology_when_actual_duties_prove_it(config):
    current = score(
        config,
        "nomura_professionals",
        "Nomura",
        "Trading Support",
        NOMURA_BODY,
        seniority_hint="junior",
    )
    assert current.desk == ["TRADING_TECH"] and current.score_breakdown.trading == 22
    assert current.score_breakdown.front_office == 15 and current.score_breakdown.total > 0
    for body in [
        NOMURA_BODY.replace("R ole & Responsibilities", "About the company"),
        NOMURA_BODY.replace("Develop and manage quantitative analytics.", "Reconcile positions."),
        NOMURA_BODY.replace("<p>", "<p hidden>"),
    ]:
        assert score(config, "nomura_professionals", "Nomura", "Trading Support", body).desk != [
            "TRADING_TECH"
        ]
    assert score(config, "other", "Nomura", "Trading Support", NOMURA_BODY).desk != ["TRADING_TECH"]
    assert score(config, "nomura_professionals", "Other", "Trading Support", NOMURA_BODY).desk != [
        "TRADING_TECH"
    ]
