import asyncio
from copy import deepcopy
from urllib.parse import parse_qs

import httpx
import pytest

from tests.test_source_expansion166 import profile
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.scotiabank import ROOT, ScotiabankCollector, detail, job_url, parse_page


def row(identifier=1):
    return dict(
        id=str(identifier),
        title="Quantitative Analyst - Off-Cycle Intern",
        url=ROOT + f"/job/London-Quantitative-Analyst/{identifier}/",
        location="London, GB",
        posted="2026-10-14",
    )


def page(rows, total=None, offset=0, term="trading"):
    total = len(rows) if total is None else total
    label = (
        f'<span class="paginationLabel">Results {offset + 1} – {offset + len(rows)} of {total}</span>'
        if rows
        else '<div id="noresults-message">Your search returned no results.</div>'
    )
    return (
        f'<input name="q" value="{term}">'
        + label
        + "<table>"
        + "".join(
            '<tr class="data-row"><td><a class="jobTitle-link" href="'
            + r["url"]
            + '">'
            + r["title"]
            + "</a></td>"
            '<td headers="hdrLocation">'
            + r["location"]
            + '</td><td headers="hdrDate">Oct 14, 2026</td></tr>'
            for r in rows
        )
        + "</table>"
    )


def posting(r=None):
    r = r or row()
    return (
        "<h1>Title: "
        + r["title"]
        + '</h1><span class="jobdescription"><p>Requisition ID: 12345</p>'
        "<h2>The role</h2><p>Scotiabank offers a six-month off-cycle internship. Start date: 1 September 2027.</p>"
        "<h2>Responsibilities</h2><p>Research systematic trading strategies, derivatives and pricing for the trading desk.</p>"
        "<h2>Requirements</h2><ul><li>Previous quantitative research experience preferred.</li></ul></span>"
    )


def collect(monkeypatch, *, repeat=False, changed=False, changed_detail=False, limit=150):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    rows = [row(i + 1) for i in range(26)]
    calls = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls.append(str(request.url))
        if request.url.path == "/search/":
            offset = int(parse_qs(request.url.query.decode())["startrow"][0])
            values = rows[offset : offset + 25]
            if repeat and offset:
                values = [rows[0]]
            if changed and not offset and len(calls) > 1:
                values = deepcopy(values)
                values[0]["location"] = "Paris, FR"
            return httpx.Response(200, text=page(values, total=26, offset=offset))
        r = next(r for r in rows if r["url"] == str(request.url))
        t = posting(r)
        if changed_detail:
            t = t.replace(r["title"], "Other Trader")
        return httpx.Response(200, text=t)

    async def run():
        h = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            c = profile("scotiabank")
            c.options["search_terms"] = ["trading"]
            c.options["max_details"] = limit
            return await ScotiabankCollector("scotiabank", c, h).collect()
        finally:
            await h.close()

    return asyncio.run(run()), calls


def test_full_pagination_description_and_calendar_date(monkeypatch):
    c, calls = collect(monkeypatch)
    assert len(c.jobs) == 26 and c.scope_complete and not c.complete
    assert c.selection.examined == c.selection.selected == 26
    assert len(calls) == 29
    j = c.jobs[0]
    assert j.publication_day.isoformat() == "2026-10-14"
    assert j.date_posted is None and j.application_deadline is None
    assert j.location == "London, GB" and "<h2>Requirements</h2>" in j.description
    assert "experience preferred" in j.description
    assert j.minimum_experience_years is None and j.expected_start_date is None


@pytest.mark.parametrize("flag", ["repeat", "changed", "changed_detail"])
def test_live_catalogue_or_detail_changes_are_not_successes(monkeypatch, flag):
    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, **{flag: True})


def test_detail_limit_refuses_incomplete_success(monkeypatch):
    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, limit=25)


@pytest.mark.parametrize("change", ["query", "count", "duplicate", "date", "location", "url"])
def test_search_integrity(change):
    rows = [row(i + 1) for i in range(25)]
    t = page(rows)
    if change == "query":
        t = t.replace('value="trading"', 'value="other"')
    elif change == "count":
        t = t.replace("of 25", "of 24")
    elif change == "duplicate":
        t = t.replace("/26/", "/1/").replace("/25/", "/1/")
    elif change == "date":
        t = t.replace("Oct 14, 2026", "today")
    elif change == "location":
        t = t.replace("London, GB", "")
    else:
        t = t.replace(ROOT, "https://example.com")
    with pytest.raises(SourceUnavailable):
        parse_page(t, "trading", 0, 1000)


def test_empty_is_verified_and_nonempty_error_is_not_empty():
    assert parse_page(page([]), "trading", 0, 1000) == ([], 0)
    with pytest.raises(SourceUnavailable):
        parse_page('<input name="q" value="trading"><p>Error</p>', "trading", 0, 1000)


@pytest.mark.parametrize("suffix", ["?private=1", "#fragment", "/../1/"])
def test_job_url_scope(suffix):
    with pytest.raises(SourceUnavailable):
        job_url(row()["url"] + suffix)


def test_published_md_subsidiary_route_keeps_the_same_origin_and_identity():
    url = ROOT + "/MD/job/Sydney-Advisor-Associate-MD-Wealth-Sydney-NS-B3L2C1/606106017/"
    assert job_url(url) == (url, "606106017")
    with pytest.raises(SourceUnavailable):
        job_url(url.replace("/MD/", "/unverified/"))
    tangerine = ROOT + "/Tangerine/job/Toronto-Principal-AI-Engineer-Tangerine-ON/604347617/"
    assert job_url(tangerine) == (tangerine, "604347617")
    jfl = ROOT + "/JFL/job/Toronto-Senior-Administrator-ON/605601617/"
    assert job_url(jfl) == (jfl, "605601617")


def test_hidden_text_and_scripts_never_become_candidate_facts():
    t = posting().replace(
        "</span>", "<span hidden>Start date: 1 January 2020.</span><script>secret</script></span>"
    )
    j = detail(t, row(), "scotiabank")
    assert "2020" not in j.description and "secret" not in j.description
