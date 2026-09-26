import pytest

from trading_radar.config import load_config
from trading_radar.education import education_mentions
from trading_radar.missions import mission_excerpts
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.targeting import tp_broking_duties
from trading_radar.workday import WorkdayCollector, workday_base

QUOTES = "<p>Role Responsibilities:</p><ul><li>Identify trade opportunities and calculate strategies.</li><li>Give live quotes to traders through the messaging systems.</li><li>Liaise with clients.</li></ul>"
EXECUTION = "<p>Role Responsibilities</p><ul><li>Arrange or introduce trades from client orders.</li><li>Develop existing and new client relationships.</li><li>Understand the underlying products being traded by clients.</li></ul>"


def broker(raw, config, content=QUOTES, **updates):
    values = dict(
        source="tp_icap", company="TP ICAP", title="Trainee Broker, Spot FX", description=content
    )
    values.update(updates)
    return score_job(normalize(raw.model_copy(update=values)), config.keywords)


@pytest.mark.parametrize(
    "content", [QUOTES, EXECUTION, QUOTES.replace("Role Responsibilities", "Responsibilities")]
)
def test_broking_requires_client_quotes_or_execution_not_corporate_presentation(
    raw, config, content
):
    job = broker(raw, config, content)
    assert job.desk == ["BROKING"] and job.seniority == "junior"
    assert job.score_breakdown.trading == 22
    assert job.score_breakdown.front_office == 15
    assert "CRYPTO" not in broker(raw, config, "<p>We trade crypto.</p>" + content).asset_class
    assert mission_excerpts(job)


@pytest.mark.parametrize(
    "content",
    [
        "<p>About us</p>" + QUOTES.replace("Role Responsibilities:", "Corporate services"),
        QUOTES + QUOTES,
        QUOTES + QUOTES.replace("Role Responsibilities", "Responsibilities"),
        "<section hidden>" + QUOTES + "</section>",
        QUOTES.replace("Give live quotes to traders", "Enter trade records"),
        QUOTES.replace("Give live quotes to traders", "Do not give live quotes to traders"),
        "<p>Role Responsibilities</p><ul><li>Provide support to brokers. Book and reconcile trades.</li></ul>",
    ],
)
def test_unverified_operational_or_ambiguous_broking_is_not_promoted(raw, config, content):
    assert not tp_broking_duties(broker(raw, config, content))


@pytest.mark.parametrize(
    "updates",
    [
        {"source": "other"},
        {"source_type": "aggregator"},
        {"company": "Other"},
        {"title": "Broker Operations Analyst"},
        {"title": "Associate Broker"},
    ],
)
def test_broking_scope_identity_and_title(raw, config, updates):
    assert not tp_broking_duties(broker(raw, config, **updates))


def test_technology_evidence_is_from_the_role_and_keeps_experience(raw, config):
    duties = "<p>Role Responsibilities</p><ul><li>Work closely with Quants on implementation of trading algorithms, quantitative models and analytical signals.</li><li>Build low latency trading strategies.</li></ul><p>Experience/Competences</p><p>Requires 6 years experience.</p>"
    job = broker(raw, config, duties, title="Algorithmic Trading Developer")
    assert "TRADING_TECH" in job.desk
    assert "software role without embedded trading evidence" not in job.score_breakdown.exclusions
    assert "requires at least 5 years of experience" in job.score_breakdown.exclusions
    changed = broker(
        raw,
        config,
        duties.replace("Role Responsibilities", "About us"),
        title="Algorithmic Trading Developer",
    )
    assert "software role without embedded trading evidence" in changed.score_breakdown.exclusions


@pytest.mark.parametrize(
    ("source", "tenant", "site"),
    [
        ("bp", "bpinternational", "bpCareers"),
        ("shell", "shell", "ShellCareers"),
        ("tp_icap", "tp", "TP-ICAP"),
    ],
)
def test_config_has_verified_portals_bounded_queries_and_operational_exclusions(
    source, tenant, site
):
    co = load_config().companies[source]
    public, api = workday_base(co)
    assert co.enabled and co.scan_interval == 1800 and co.tenant == tenant
    assert public.endswith("/" + site) and api.endswith("/" + tenant + "/" + site)
    collector = WorkdayCollector(source, co, None)
    for title in [
        "Trading Operator",
        "Sr. Sanctions Advisor - Trading & Supply",
        "Market Data & Trading Systems Engineer",
        "Trading Operations Analyst",
    ]:
        assert not collector.selected(title)
    assert collector.selected("Graduate Trading Analyst")


def test_new_employer_degree_and_mission_sections(job):
    job.source = "bp"
    job.description = "<p>To be eligible for the ST&S graduate programme you should:</p><ul><li>Be pursuing a bachelor's or master's degree in any discipline.</li></ul>"
    assert education_mentions(job)["levels"] == ["bachelor", "master"]
    job.source = "shell"
    job.description = "<p>What you’ll be doing</p><ul><li>Price gas options within limits.</li></ul><p>What you bring</p><ul><li>BSc or MSc in a quantitative discipline.</li></ul>"
    assert mission_excerpts(job)["excerpts"] == ["Price gas options within limits."]
    assert education_mentions(job)["levels"] == ["bachelor", "master"]


def test_internal_quotes_and_operational_support_are_not_client_broking(raw, config):
    content = "<p>Role Responsibilities</p><ul><li>Provide complete support to the brokers.</li><li>Ensure timely input of trades into trading systems.</li><li>Provide live quotes through the link line to our internal regional offices.</li><li>Monitor markets and follow financial news and developments.</li></ul>"
    job = broker(raw, config, content, title="Trainee Broker, Forward FX")
    assert not tp_broking_duties(job)
    assert job.score_breakdown.total == 0


@pytest.mark.parametrize(
    "title", ["Associate Broker", "Senior Trainee Broker", "Trainee Broker Internship"]
)
def test_new_section_keeps_seniority_and_internship_exclusions(raw, config, title):
    job = broker(
        raw, config, QUOTES.replace("Role Responsibilities", "Responsibilities"), title=title
    )
    assert job.score_breakdown.total == 0
