import asyncio
import json

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.societe_generale import DIRECTORIES, directory, job_url, parse_detail


def config(**options):
    return Company(
        name="Société Générale",
        ats="societe_generale",
        career_url=DIRECTORIES["fr"],
        request_interval=0.1,
        options=options,
    )


def link(identifier="26000ABC", lang="en"):
    route = "offres-d-emploi" if lang == "fr" else "en/job-offers"
    return f"https://careers.societegenerale.com/{route}/trading-analyst-{identifier}-{lang}"


def card(identifier="26000ABC", lang="en", title="Trading Analyst"):
    return f'<div data-offer-id="{identifier}"><a href="{link(identifier, lang)}">{title}</a><span>Paris</span></div>'


def listing(cards, count=None):
    total = len(cards) if count is None else count
    return f'<span class="text-extra-large"><strong>{total}</strong>offre(s)</span>' + "".join(
        cards
    )


def info(identifier="26000ABC"):
    return {
        "@type": "JobPosting",
        "identifier": {"value": identifier},
        "title": "Trading Analyst - Corporate & Investment Banking - Paris",
        "description": "Structured fallback description",
        "datePosted": "2026/09/07",
        "validThrough": "2026/11/30",
        "employmentType": "Permanent",
        "jobLocation": {"address": {"addressLocality": "Paris", "addressCountry": "France"}},
    }


def detail(identifier="26000ABC", lang="en", start=None, record=None):
    start = start or ("30/11/2026" if lang == "fr" else "2026/11/30")
    reference, started, published = (
        ("Référence", "Date de début", "Date de publication")
        if lang == "fr"
        else ("Reference", "Start date", "Publication date")
    )
    date = "07/09/2026" if lang == "fr" else "2026/09/07"
    return f'''<html><link rel="canonical" href="{link(identifier, lang)}">
    <script type="application/ld+json">{json.dumps(record or info(identifier))}</script>
    <h1 id="offerTitle">Trading <span>Analyst</span></h1>
    <div><span>{reference}</span> {identifier}</div>
    <div><span>{started}</span> {start}</div>
    <div><span>{published}</span> {date}</div>
    <section id="job-detail-description"><h2>Missions</h2><p>Trade rates<br>Price options</p></section>
    <section id="job-detail-profile"><h2>Profile</h2><p>Python, 0-2 years</p></section>
    <section id="job-detail-group"><p>Our company</p></section></html>'''


def row(identifier="26000ABC", lang="en"):
    return {
        "id": identifier,
        "url": link(identifier, lang),
        "language": lang,
        "title": "Trading Analyst",
    }


def execute(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("sg", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_two_directories_merge_references_before_detail(monkeypatch):
    details = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if str(req.url) == DIRECTORIES["fr"]:
            return httpx.Response(200, text=listing([card(lang="fr"), card("26000DEF", lang="fr")]))
        if str(req.url) == DIRECTORIES["en"]:
            return httpx.Response(
                200, text=listing([card(), card("26000ZZZ", title="Trading Operations")])
            )
        details.append(str(req.url))
        _, identifier, lang = job_url(str(req.url))
        return httpx.Response(200, text=detail(identifier, lang))

    result = execute(handler, monkeypatch)
    assert len(result.jobs) == 2 and not result.complete and result.requests == 5
    assert set(details) == {link(), link("26000DEF", "fr")}
    assert {j.external_id for j in result.jobs} == {"26000ABC", "26000DEF"}


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_visible_title_full_description_and_real_start_date(lang):
    job = parse_detail(detail(lang=lang), row(lang=lang), config(), "sg")
    assert job.title == "Trading Analyst"  # No business-unit suffix that would exclude the job.
    assert (
        "Python" in job.description
        and "Price options" in job.description
        and "Our company" in job.description
    )
    assert job.location == "Paris, France"
    assert job.expected_start_date == "2026-11-30"
    assert job.date_posted.isoformat() == "2026-09-07T00:00:00+00:00"
    assert job.application_deadline is None


def test_immediate_start_does_not_become_deadline():
    job = parse_detail(detail(start="Immediately"), row(), config(), "sg")
    assert job.expected_start_date == "Immediately" and job.application_deadline is None


def span_header(body):
    # Audited public layout: each header value now lives in a span whose only
    # child element is the bold label; the value remains a direct text node.
    return body.replace("<div><span>", '<span class="font-title"><span class="font-bold">').replace(
        "</div>", "</span>"
    )


@pytest.mark.parametrize("lang", ["fr", "en"])
@pytest.mark.parametrize("start", [None, "Immediately"])
def test_span_header_matches_original_metadata_without_guessing(lang, start):
    body = detail(lang=lang, start=start)
    old = parse_detail(body, row(lang=lang), config(), "sg")
    new = parse_detail(span_header(body), row(lang=lang), config(), "sg")
    assert new.model_dump() == old.model_dump()
    assert new.application_deadline is None


@pytest.mark.parametrize(
    "change,match",
    [
        (
            lambda s: s.replace("Reference</span> 26000ABC", "Reference</span> 26000XYZ"),
            "reference",
        ),
        (lambda s: s.replace("Reference</span> 26000ABC", "Reference</span>"), "metadata"),
        (
            lambda s: s.replace("Reference</span> 26000ABC", "Reference</span><b>26000ABC</b>"),
            "metadata",
        ),
        (
            lambda s: s.replace("Reference</span> 26000ABC", "Reference</span> 26000ABC other"),
            "reference",
        ),
        (lambda s: s + "<div><span>Reference</span>26000ABC</div>", "ambiguous"),
        (lambda s: s + "<span><span>Reference</span>26000XYZ</span>", "ambiguous"),
        (
            lambda s: s.replace(
                "Publication date</span> 2026/09/07", "Publication date</span> 2026/09/08"
            ),
            "disagree",
        ),
        (
            lambda s: s.replace("Start date</span> 2026/11/30", "Start date</span> 2026/99/99"),
            "invalid SG date",
        ),
        (lambda s: s.replace('"value": "26000ABC"', '"value": "26000XYZ"'), "identifier"),
        (lambda s: s.replace('rel="canonical"', 'rel="other"'), "canonical"),
    ],
)
def test_span_layout_preserves_identity_and_date_checks(change, match):
    with pytest.raises(SourceUnavailable, match=match):
        parse_detail(change(span_header(detail())), row(), config(), "sg")


@pytest.mark.parametrize(
    "body,match",
    [
        ("<html>Challenge</html>", "count missing"),
        (listing([card()], 2), "incomplete"),
        (listing([card(), card()]), "duplicate"),
        (listing([card(lang="fr")]), "language"),
        (
            listing([card()]).replace('data-offer-id="26000ABC"', 'data-offer-id="26000XYZ"'),
            "identity",
        ),
        (listing([card()]).replace("Trading Analyst", ""), "identity"),
        (listing([], 2000), "limit"),
    ],
)
def test_directory_drift_fails_closed(body, match):
    with pytest.raises(SourceUnavailable, match=match):
        directory(body, "en", 1999)


@pytest.mark.parametrize(
    "url",
    [
        link().replace("careers.societegenerale.com", "evil.example"),
        link().replace("https:", "http:"),
        link() + "?token=x",
        link() + "#other",
        link().replace("-en", "-fr"),
        link().replace("trading-analyst-", "../"),
    ],
)
def test_only_verified_job_routes(url):
    with pytest.raises(SourceUnavailable):
        job_url(url)


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda s: s.replace('id="job-detail-profile"', 'id="missing-profile"'), "requirements"),
        (lambda s: s.replace("<p>Python, 0-2 years</p>", ""), "requirements"),
        (lambda s: s.replace('id="offerTitle"', 'id="missing-title"'), "title missing"),
        (lambda s: s.replace('rel="canonical"', 'rel="other"'), "canonical"),
        (lambda s: s.replace('"value": "26000ABC"', '"value": "26000XYZ"'), "identifier"),
        (
            lambda s: s.replace("Reference</span> 26000ABC", "Reference</span> 26000XYZ"),
            "reference",
        ),
        (
            lambda s: s.replace(
                "Publication date</span> 2026/09/07", "Publication date</span> 2026/09/08"
            ),
            "disagree",
        ),
        (
            lambda s: s.replace("Start date</span> 2026/11/30", "Start date</span> 2026/99/99"),
            "invalid SG date",
        ),
        (
            lambda s: s.replace(
                '"jobLocation": {"address": {"addressLocality": "Paris", "addressCountry": "France"}}',
                '"jobLocation": null',
            ),
            "location",
        ),
    ],
)
def test_bad_details_abort(change, match):
    with pytest.raises(SourceUnavailable, match=match):
        parse_detail(change(detail()), row(), config(), "sg")


def test_one_directory_failure_does_not_fetch_or_return_partial_details(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if str(req.url) == DIRECTORIES["fr"]:
            return httpx.Response(200, text=listing([card(lang="fr")]))
        assert str(req.url) == DIRECTORIES["en"]
        return httpx.Response(403)

    with pytest.raises(SourceUnavailable, match="403"):
        execute(handler, monkeypatch)


def test_detail_budget(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        lang = "fr" if str(req.url) == DIRECTORIES["fr"] else "en"
        return httpx.Response(200, text=listing([card(lang=lang), card("26000DEF", lang)]))

    with pytest.raises(SourceUnavailable, match="detail limit"):
        execute(handler, monkeypatch, max_details=1)


def test_keywords_not_silently_ignored():
    from trading_radar.societe_generale import SocieteGeneraleCollector

    with pytest.raises(ValueError):
        SocieteGeneraleCollector("sg", config(search_terms=["trading"]), None)
