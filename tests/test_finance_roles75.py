import pytest

from trading_radar.config import load_config
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.targeting import finance_role_evidence

CASES = [
    (
        "squarepoint_capital",
        "Junior Quant Researcher",
        "research",
        "Position Overview",
        "Required Qualifications",
        [
            "Research and implement strategies within the firm’s automated trading framework.",
            "Identify trading opportunities.",
            "Researching and implementing trading ideas.",
        ],
    ),
    (
        "squarepoint_capital",
        "Junior Quant Researcher - ML Alpha Research",
        "research",
        "Position Overview",
        "Required Qualifications",
        [
            "Identify trading opportunities.",
            "Researching new statistical and ML techniques.",
            "Deploy and monitor models used to generate trading signals.",
        ],
    ),
    (
        "squarepoint_capital",
        "Junior Quant Developer",
        "technology",
        "Position Overview",
        "Required Qualifications",
        [
            "Implement novel trading strategies.",
            "Identify new trading opportunities.",
            "Backtesting simulations.",
        ],
    ),
    (
        "squarepoint_capital",
        "Graduate Quant Developer",
        "technology",
        "Role and Responsibilities",
        "Required Qualifications",
        [
            "Software engineering skills to support investment research and trading.",
            "Work closely with quantitative researchers.",
            "Workflows for alpha generation.",
            "Frameworks used by researchers and traders globally.",
        ],
    ),
    (
        "chicago_trading_campus",
        "Systematic Quantitative Researcher - PhD",
        "research",
        "The Role",
        "Qualifications PhD in Science or Engineering fields",
        [
            "Trading strategy generation.",
            "Back-testing.",
            "Statistical analysis.",
            "Build predictive and explanatory models.",
            "Trading infrastructure.",
        ],
    ),
    (
        "dv_trading",
        "Quantitative Researcher",
        "research",
        "Responsibilities",
        "Requirements",
        [
            "Develop and refine signals grounded in market microstructure analysis.",
            "Collaborate with traders to translate research into deployable strategies.",
            "Signal research, backtesting, and production deployment.",
        ],
    ),
]


@pytest.mark.parametrize("source,title,role,start,end,clauses", CASES)
def test_audited_roles_require_bounded_visible_duties(source, title, role, start, end, clauses):
    cfg = load_config()
    body = " ".join(clauses)
    content = f"<p>{start}</p><p>{body}</p><p>{end}</p><p>A degree is preferred.</p>"
    raw = RawJob(
        company=cfg.companies[source].name,
        source=source,
        source_type="official",
        title=title,
        apply_url="https://example.test/job",
        description=content,
    )
    job = score_job(normalize(raw), cfg.keywords)
    assert finance_role_evidence(job, role)
    assert job.score_breakdown.trading == 22 and job.score_breakdown.front_office == 15
    assert ("QUANT_RESEARCH" if role == "research" else "TRADING_TECH") in job.desk
    # Description changes, identity changes and hidden content must withdraw the proof.
    for changed in [
        content.replace(start, "About us"),
        content.replace(end, "About us"),
        content.replace(clauses[0], "Unrelated duties."),
        content.replace(f"<p>{body}</p>", f"<p hidden>{body}</p>"),
        content.replace(f"<p>{body}</p>", f"<script>{body}</script>"),
        content + f"<p>{end}</p>",
    ]:
        assert not finance_role_evidence(
            normalize(raw.model_copy(update={"description": changed})), role
        )
    for fields in [
        {"source": "other"},
        {"company": "Other Firm"},
        {"source_type": "board"},
        {"title": "Different Quant Researcher"},
    ]:
        assert not finance_role_evidence(normalize(raw.model_copy(update=fields)), role)


def test_squarepoint_desk_quant_support_is_not_promoted_by_firm_language():
    raw = RawJob(
        company="Squarepoint Capital",
        source="squarepoint_capital",
        source_type="official",
        title="Desk Quant Analyst",
        apply_url="https://example.test/job",
        description="<p>Position Overview</p><p>Monitor production systems, post-trade analysis and reconciliation.</p><p>Required Qualifications</p><p>Degree.</p>",
    )
    scored = score_job(normalize(raw), load_config().keywords)
    assert scored.score_breakdown.total == 0
