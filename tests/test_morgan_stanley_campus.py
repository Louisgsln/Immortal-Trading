"""Synthetic Oleeo contracts; no sessions, employer descriptions or network calls."""

import asyncio

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.morgan_stanley_campus import BOARD, canonical_detail


def row(i=1, title="2027 Markets Off-Cycle Internship"):
    return (
        f'<tr data-oppid="{i}" data-title="{title}"><td><a class="subject" '
        f'href="/vx/lang-en-GB/mobile-0/brand-2/xf-test/candidate/so/pm/1/pl/1/opp/{i}-programme/en-GB">{title}</a></td><td>London</td></tr>'
    )


def board(rows, total=1, next_page=None):
    return (
        '<h1 class="job-board-title">Global Programs</h1>'
        f'<div class="results_meta">{total} results match</div><div id="results_list"><table>{rows}</table></div>'
        + (
            f'<span class="next_links"><a href="?start={next_page}">Next page</a></span>'
            if next_page
            else ""
        )
    )


def detail(title="2027 Markets Off-Cycle Internship", city="London"):
    fields = {
        "City": city,
        "Program": "Off-Cycle Internship",
        "Job description": '<p>Placement: six months.</p><p><strong>Requirements</strong></p><ul><li>Python.</li></ul><script>secret</script><input value="secret">',
    }
    return f"<h1>{title}</h1>" + "".join(
        f'<div class="form-group" data-field_id="{i}"><span class="hform_lbl_text">{k}</span><div class="form-control-static">{v}</div></div>'
        for i, (k, v) in enumerate(fields.items())
    )


def collect(monkeypatch, handler):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            co = Company(
                name="Morgan Stanley",
                ats="morgan_stanley_campus",
                career_url=BOARD,
                request_interval=0.1,
            )
            return await build_collector("morgan_stanley_campus", co, http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_public_programmes_pagination_and_safe_description(monkeypatch):
    paths = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        paths.append(str(req.url))
        if "jobboard" in req.url.path:
            start = int(req.url.params.get("start", 0))
            rows = "".join(row(i) for i in range(start + 1, min(start + 51, 52)))
            return httpx.Response(200, text=board(rows, 51, 50 if start == 0 else None))
        return httpx.Response(200, text=detail())

    result = collect(monkeypatch, handler)
    assert result.scope_complete and not result.complete and len(result.jobs) == 51
    assert result.selection.selected == 51
    assert all("xf-" not in p and "/apply" not in p for p in paths)
    assert (
        "<li>Python.</li>" in result.jobs[0].description
        and "secret" not in result.jobs[0].description
    )
    assert result.jobs[0].date_posted is None and result.jobs[0].expected_start_date is None


@pytest.mark.parametrize(
    "bad",
    [
        board(row(), 2),
        board(row() + row(), 2),
        board(row(), 1, 50),
        board(row()).replace("Global Programs", "Events"),
        board(row()).replace('data-title="2027', 'data-title="2028'),
    ],
)
def test_rejects_incomplete_or_event_boards(monkeypatch, bad):
    def handler(req):
        return (
            httpx.Response(404) if req.url.path == "/robots.txt" else httpx.Response(200, text=bad)
        )

    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, handler)


@pytest.mark.parametrize(
    "bad",
    [
        detail(title="Other role"),
        detail(city="Paris"),
        detail().replace("Job description", "Hidden description"),
    ],
)
def test_detail_disagreement_commits_nothing(monkeypatch, bad):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=board(row()) if "jobboard" in req.url.path else bad)

    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, handler)


def test_one_campus_title_conflict_is_quarantined_while_verified_jobs_continue(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if "jobboard" in req.url.path:
            return httpx.Response(200, text=board(row(1) + row(2), 2))
        return httpx.Response(
            200, text=detail("Other programme") if "/opp/2-" in req.url.path else detail()
        )

    result = collect(monkeypatch, handler)
    assert [job.external_id for job in result.jobs] == ["1"]
    assert len(result.conflicts) == 1
    assert result.conflicts[0].external_id == "2" and result.conflicts[0].fields == ["title"]
    assert not result.complete and not result.scope_complete


def test_campus_forbidden_detail_does_not_become_an_identity_conflict(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if "jobboard" in req.url.path:
            return httpx.Response(200, text=board(row(1) + row(2), 2))
        return (
            httpx.Response(403) if "/opp/2-" in req.url.path else httpx.Response(200, text=detail())
        )

    with pytest.raises(SourceUnavailable, match="HTTP 403"):
        collect(monkeypatch, handler)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/vx/lang-en-GB/candidate/so/pm/1/pl/1/opp/1-test/en-GB",
        "/vx/lang-en-GB/candidate/so/pm/1/pl/2/opp/1-test/en-GB",
        "/vx/lang-en-GB/candidate/so/pm/1/pl/1/opp/2-test/en-GB",
    ],
)
def test_detail_links_fail_closed(url):
    with pytest.raises(SourceUnavailable):
        canonical_detail(url, "1")


def test_existing_public_vendor_session_does_not_need_xf_in_link():
    url = "/vx/lang-en-GB/mobile-0/brand-2/candidate/so/pm/1/pl/1/opp/1-programme/en-GB"
    assert (
        canonical_detail(url, "1")
        == "https://morganstanley.tal.net/vx/lang-en-GB/candidate/so/pm/1/pl/1/opp/1-programme/en-GB"
    )


def test_identical_responsive_board_headings_are_allowed():
    from trading_radar.morgan_stanley_campus import MorganStanleyCampusCollector

    config = Company(name="Morgan Stanley", ats="morgan_stanley_campus", career_url=BOARD)
    collector = MorganStanleyCampusCollector("morgan_stanley_campus", config, None)
    text = board(row()) + '<h1 class="job-board-title">Global Programs</h1>'
    assert collector.listing(text, 0)[0] == 1


def test_quant_finance_requires_trading_duties_inside_labelled_dom_section():
    from trading_radar.models import RawJob
    from trading_radar.normalizer import normalize
    from trading_radar.targeting import research_trading_evidence

    body = "<p><strong>Roles and Responsibilities</strong><br><ul><li>Build pricing models and hedging strategies that drive trading decisions.</li></ul></p><p><strong>Qualifications/Skills/Requirements</strong></p><ul><li>Python.</li></ul>"
    raw = RawJob(
        company="Morgan Stanley",
        source="morgan_stanley_campus",
        source_type="official",
        title="2027 Quantitative Finance Off-Cycle Internship (London)",
        apply_url="https://example.com/job",
        description=body,
    )
    assert research_trading_evidence(normalize(raw))
    assert not research_trading_evidence(
        normalize(
            raw.model_copy(
                update={"description": body.replace("Roles and Responsibilities", "Firm overview")}
            )
        )
    )
    assert not research_trading_evidence(normalize(raw.model_copy(update={"source": "other"})))
