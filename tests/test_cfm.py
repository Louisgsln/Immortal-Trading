import asyncio
from copy import deepcopy
from urllib.parse import parse_qs

import httpx
import pytest

from tests.test_source_expansion166 import profile
from trading_radar.cfm import ROOT, CFMCollector, detail, job_url, listing
from trading_radar.collectors import build_collector
from trading_radar.http import HTTPClient, SourceUnavailable


def row(identifier=1):
    return dict(
        id=str(identifier),
        title="Portfolio Engineering - Internship",
        url=ROOT + f"/job/Paris-Portfolio-Engineering-Internship/{identifier}/",
        location="Paris, 75, FR",
        department="Portfolio Analytics",
    )


def page(rows, total=None, offset=0):
    total = len(rows) if total is None else total
    if not rows:
        return (
            '<input name="q" value=""><div id="noresults-message">'
            "The 0 most recent jobs posted by Capital Fund Management are listed below for your convenience."
            "</div>"
        )
    return (
        '<input name="q" value="">'
        f"<span>Showing {offset + 1} to {offset + len(rows)} of {total} Jobs</span>"
        f'<ul id="job-tile-list" data-per-page="25" data-record-returned="{len(rows)}">'
        + "".join(
            '<li class="job-tile" data-url="'
            + r["url"]
            + '">'
            + (f'<a class="jobTitle-link" href="{r["url"]}">{r["title"]}</a>' * 3)
            + f'<div id="job-{r["id"]}-desktop-section-location-value">{r["location"]}</div>'
            + f'<div id="job-{r["id"]}-desktop-section-dept-value">{r["department"]}</div></li>'
            for r in rows
        )
        + "</ul>"
    )


def posting(r=None):
    r = r or row()
    return (
        f'<link rel="canonical" href="{r["url"]}"><h1>{r["title"]}</h1>'
        '<span class="jobdescription"><h2>ABOUT CFM</h2>'
        "<p>Capital Fund Management is a quantitative and systematic investment manager.</p>"
        "<h2>Your Role</h2><p>Join our portfolio analytics team for a six-month off-cycle internship.</p>"
        "<h2>Key Responsibilities</h2><ul><li>Research portfolio construction and systematic trading strategies.</li></ul>"
        "<h2>Your Skills</h2><ul><li>Quantitative research experience preferred. Python and statistics.</li></ul>"
        "<h2>EQUAL OPPORTUNITIES STATEMENT</h2><p>We welcome all qualified applicants.</p></span>"
    )


def collect(
    monkeypatch, *, second=None, repeat=False, changed_detail=False, options=None, excluded=False
):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    rows = [row(i + 1) for i in range(26)]
    if excluded:
        rows[-1]["title"] = "Quant Infrastructure Engineer"
    calls = []

    def handler(req):
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        calls.append(str(req.url))
        if req.url.path == "/search/":
            query = parse_qs(req.url.query.decode(), keep_blank_values=True)
            assert query["q"] == [""] and query["sortColumn"] == ["referencedate"]
            offset = int(query["startrow"][0])
            values = rows[offset : offset + 25]
            if repeat and offset:
                values = [rows[0]]
            if second and not offset and len(calls) > 1:
                values = deepcopy(values)
                values[0].update(second)
            return httpx.Response(200, text=page(values, total=26, offset=offset))
        r = next(r for r in rows if r["url"] == str(req.url))
        text = posting(r)
        if changed_detail:
            text = text.replace("<h1>" + r["title"], "<h1>Other Trader")
        return httpx.Response(200, text=text)

    async def run():
        h = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            c = profile("cfm")
            if options:
                c.options.update(options)
            return await build_collector("cfm", c, h).collect()
        finally:
            await h.close()

    return asyncio.run(run()), calls


def test_whole_catalogue_pagination_full_descriptions_and_partial_closure_scope(monkeypatch):
    result, calls = collect(monkeypatch, excluded=True)
    assert len(result.jobs) == 25 and result.scope_complete and not result.complete
    assert result.selection.examined == 26 and result.selection.selected == 25
    assert len(calls) == 28
    raw = result.jobs[0]
    assert raw.location == "Paris, 75, FR" and "<h2>Your Skills</h2>" in raw.description
    assert "experience preferred" in raw.description and "six-month" in raw.description
    assert raw.date_posted is None and raw.publication_day is None
    assert raw.minimum_experience_years is None and raw.application_deadline is None
    assert raw.employment_type is None and raw.expected_start_date is None


@pytest.mark.parametrize(
    "change", [{"title": "Other Quant"}, {"location": "London"}, {"department": "Research"}]
)
def test_listing_change_during_detail_collection_fails(monkeypatch, change):
    with pytest.raises(SourceUnavailable, match="changed"):
        collect(monkeypatch, second=change)


@pytest.mark.parametrize("flag", ["repeat", "changed_detail"])
def test_repeated_pagination_or_wrong_detail_is_not_success(monkeypatch, flag):
    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, **{flag: True})


@pytest.mark.parametrize("options", [{"max_results_per_query": 25}, {"max_details": 25}])
def test_bounds_never_return_a_truncated_success(monkeypatch, options):
    with pytest.raises(SourceUnavailable):
        collect(monkeypatch, options=options)


@pytest.mark.parametrize(
    "change",
    ["query", "count", "duplicate", "location", "department", "anchor", "page_size", "returned"],
)
def test_listing_contract_integrity(change):
    text = page([row()])
    if change == "query":
        text = text.replace('value=""', 'value="trading"')
    elif change == "count":
        text = text.replace("of 1 Jobs", "of 2 Jobs")
    elif change == "duplicate":
        text = page([row(), row()])
    elif change == "location":
        text = text.replace("Paris, 75, FR", "")
    elif change == "department":
        text = text.replace("Portfolio Analytics", "")
    elif change == "anchor":
        text = text.replace('href="' + row()["url"] + '"', 'href="' + row(2)["url"] + '"', 1)
    elif change == "page_size":
        text = text.replace('data-per-page="25"', 'data-per-page="50"')
    else:
        text = text.replace('data-record-returned="1"', 'data-record-returned="2"')
    with pytest.raises(SourceUnavailable):
        listing(text, 0, 1000)


def test_explicit_zero_is_accepted_but_error_or_empty_markup_is_not():
    assert listing(page([]), 0, 1000) == ([], 0)
    for text in [
        '<input name="q" value=""><p>Error</p>',
        "",
        page([]).replace("0 most recent", "1 most recent"),
    ]:
        with pytest.raises(SourceUnavailable):
            listing(text, 0, 1000)
    with pytest.raises(SourceUnavailable):
        listing(page([]), 25, 1000)


@pytest.mark.parametrize("suffix", ["?x=1", "#fragment", "/../1/", "/%2e%2e/1/", "\\other"])
def test_posting_url_rejects_unverified_routes(suffix):
    with pytest.raises(SourceUnavailable):
        job_url(row()["url"] + suffix)


def test_canonical_and_visible_employer_description_are_required():
    for text in [
        posting().replace('rel="canonical"', 'rel="alternate"'),
        posting().replace(row()["url"], row(2)["url"]),
        posting().replace("ABOUT CFM", "OTHER EMPLOYER"),
    ]:
        with pytest.raises(SourceUnavailable):
            detail(text, row(), "cfm")


def test_hidden_facts_and_scripts_never_become_candidate_information():
    text = posting().replace(
        "</span>",
        '<p hidden>Start date: 1 January 2020.</p><script>secret</script><p aria-hidden="true">private</p></span>',
    )
    raw = detail(text, row(), "cfm")
    assert (
        "2020" not in raw.description
        and "secret" not in raw.description
        and "private" not in raw.description
    )


def test_bold_paragraph_labels_preserve_the_same_complete_description():
    text = posting().replace("<h2>", "<p><strong>").replace("</h2>", "</strong></p>")
    raw = detail(text, row(), "cfm")
    assert "six-month" in raw.description and "experience preferred" in raw.description


@pytest.mark.parametrize("section", ["Your Role", "Your Skills"])
def test_missing_role_or_requirements_cannot_pass_as_company_introduction(section):
    text = posting().replace(section, "Other information")
    with pytest.raises(SourceUnavailable):
        detail(text, row(), "cfm")


def test_empty_skills_or_hidden_label_cannot_validate_a_partial_posting():
    for text in [
        posting().replace("Quantitative research experience preferred. Python and statistics.", ""),
        posting().replace("<h2>Your Skills</h2>", "<h2 hidden>Your Skills</h2>"),
    ]:
        with pytest.raises(SourceUnavailable):
            detail(text, row(), "cfm")


def test_only_audited_employer_owned_site_can_be_configured():
    c = profile("cfm")
    c.career_url = "https://www.cfm.com/join-us-cfm-careers/"
    with pytest.raises(ValueError, match="verified"):
        CFMCollector("cfm", c, None)
