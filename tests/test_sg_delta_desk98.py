"""Missed SG desk title: import, evidence, score, and exactly one normal alert."""

import asyncio
import html

import httpx
import pytest
from test_societe_generale import card, detail, listing, row

from trading_radar.config import load_config
from trading_radar.http import HTTPClient
from trading_radar.normalizer import normalize
from trading_radar.scanner import scan
from trading_radar.scoring import score_job
from trading_radar.societe_generale import DIRECTORIES, SocieteGeneraleCollector, parse_detail

TITLE = "V.I.E. One Delta Desk Analyst"
ITEMS = [
    "You will be able to contribute to the build out of the desk’s infrastructure. "
    "Your focus will be on the technical and innovation side with a strong focus on programming.",
    "He will be working closely with traders (but as a VIE won't be allowed to trade himself).",
    "Working on specific projects to improve trading tools and risk management of the book "
    "(automation, testing new models, new booking systems…)",
    "Pricing and back testing of trading strategies on existing datasets",
    "Risk and PNL analysis",
]


def duties(items=ITEMS):
    return (
        "<p>Tasks and responsibilities:</p><ul>"
        + "".join("<li>" + html.escape(item) + "</li>" for item in items)
        + "</ul>"
    )


def page(title=TITLE, body=None):
    return (
        detail()
        .replace("Trading <span>Analyst</span>", title)
        .replace("<p>Trade rates<br>Price options</p>", duties() if body is None else body)
    )


def parsed(title=TITLE, body=None, source="societe_generale", company=None):
    cfg = load_config()
    employer = cfg.companies["societe_generale"].model_copy(deep=True)
    if company:
        employer.name = company
    raw = parse_detail(page(title, body), row(), employer, source)
    return raw, score_job(normalize(raw), cfg.keywords)


@pytest.mark.parametrize("title", [TITLE, "VIE Delta One Desk Analyst", "Delta-One Desk Analyst"])
def test_audited_analyst_is_desk_technology_not_direct_trader(title):
    raw, job = parsed(title)
    assert raw.role_hint == "trading_technology"
    assert job.desk == ["TRADING_TECH"]
    assert job.score_breakdown.trading == 22
    assert job.score_breakdown.front_office == 15
    assert job.score_breakdown.junior == 20
    assert job.score_breakdown.total >= 70
    assert not job.score_breakdown.exclusions
    assert "won't be allowed to trade himself" in job.description_text


@pytest.mark.parametrize("index", range(len(ITEMS)))
@pytest.mark.parametrize("change", ["missing", "negated", "hidden"])
def test_missing_negated_or_hidden_duty_cannot_supply_evidence(index, change):
    items = list(ITEMS)
    if change == "missing":
        items.pop(index)
        body = duties(items)
    elif change == "negated":
        items[index] = "Not responsible for: " + items[index]
        body = duties(items)
    else:
        body = duties().replace(
            "<li>" + html.escape(ITEMS[index]), "<li hidden>" + html.escape(ITEMS[index])
        )
    raw, job = parsed(body=body)
    assert raw.role_hint is None
    assert job.score_breakdown.total == 0


@pytest.mark.parametrize(
    "body",
    [
        duties().replace("Tasks and responsibilities:", "About our company:"),
        duties() + duties(),
        "<div hidden>" + duties() + "</div>",
        "<p>Unrelated visible duties.</p><script>" + duties() + "</script>",
    ],
)
def test_wrong_ambiguous_or_hidden_section_does_not_qualify(body):
    assert parsed(body=body)[0].role_hint is None


def test_profile_or_company_section_cannot_supply_duties():
    cfg = load_config()
    body = page(body="<p>Work on unrelated operational tasks.</p>").replace(
        "<p>Python, 0-2 years</p>", duties()
    )
    assert (
        parse_detail(body, row(), cfg.companies["societe_generale"], "societe_generale").role_hint
        is None
    )


@pytest.mark.parametrize("source,company", [("other", None), ("societe_generale", "Other Bank")])
def test_evidence_is_limited_to_verified_source_and_employer(source, company):
    assert parsed(source=source, company=company)[0].role_hint is None


@pytest.mark.parametrize(
    "title",
    [
        "Service Desk Analyst",
        "VIE Risk Analyst",
        "VIE One Delta Desk Associate",
        "Senior Delta One Desk Analyst",
    ],
)
def test_unreviewed_roles_are_not_promoted(title):
    assert parsed(title=title)[1].score_breakdown.total == 0


def test_scope_keeps_exclusions_and_unknown_duties_unclassified():
    cfg = load_config().companies["societe_generale"]
    collector = SocieteGeneraleCollector("societe_generale", cfg, None)
    for title in [TITLE, "Delta One Desk Analyst", "Equity Desk Analyst"]:
        assert collector.selected(title)
    for title in [
        "Senior Delta One Desk Analyst",
        "Delta One Operations",
        "Desk Analyst Market Risk",
    ]:
        assert not collector.selected(title)
    assert parsed("Equity Desk Analyst", "<p>Unverified role.</p>")[1].score_breakdown.total == 0


@pytest.mark.parametrize(
    "field,value", [("employment_type", "Internship"), ("minimum_experience_years", 5)]
)
def test_verified_duties_never_override_eligibility_exclusions(field, value):
    raw, _ = parsed()
    raw = raw.model_copy(update={field: value})
    job = score_job(normalize(raw), load_config().keywords)
    assert job.score_breakdown.exclusions and job.score_breakdown.total == 0


@pytest.mark.parametrize(
    "field,value", [("source", "other"), ("company", "Other Bank"), ("source_type", "board")]
)
def test_persisted_hint_requires_the_verified_source_identity(field, value):
    raw, _ = parsed()
    raw = raw.model_copy(update={field: value})
    assert score_job(normalize(raw), load_config().keywords).score_breakdown.total == 0


def test_two_collections_import_once_and_queue_one_normal_alert(repo, monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    cfg = load_config()
    cfg.companies = {"societe_generale": cfg.companies["societe_generale"]}
    cfg.settings.alerts_enabled = True
    cfg.settings.bootstrap_silent = False
    cfg.settings.alert_min_score = 70

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if str(request.url) in DIRECTORIES.values():
            language = "fr" if str(request.url) == DIRECTORIES["fr"] else "en"
            return httpx.Response(
                200, text=listing([card(title=TITLE)]) if language == "en" else listing([])
            )
        return httpx.Response(200, text=page())

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            first = await scan(cfg, repo, http=http)
            second = await scan(cfg, repo, http=http)
            assert first.successful == second.successful == 1
            assert first.new == 1 and second.new == second.updated == 0
            assert first.closed == second.closed == first.alerts == second.alerts == 0
            assert len(repo.pending()) == 1
            job = repo.list_jobs()[0]
            assert job.title == TITLE and job.score_breakdown.total >= 70
            assert job.programme_type == "VIE"
        finally:
            await http.close()

    asyncio.run(run())
