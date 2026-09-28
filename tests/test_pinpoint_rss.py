"""Wolverine feed identity, publication evidence and conservative failure paths."""

import asyncio
from datetime import UTC, datetime
from html import escape

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import load_config
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.pinpoint_rss import FEED, PinpointOptions, parse_feed
from trading_radar.scoring import score_job


def content(title="Quantitative Trading Analyst", employment="Full Time"):
    return f"""<h1>{title}</h1><p><strong>Department: </strong>Trading</p>
    <p><strong>Employment Type: </strong>{employment}</p>
    <p><strong>Location: </strong>Chicago, IL</p><h3>Description</h3>
    <div>Manage a portfolio of options and execute trades.</div>
    <h3>What You’ll Do</h3><ul><li>Provide liquidity on electronic markets.</li></ul>
    <h3>What We’re Looking For</h3><ul><li>Bachelor's degree in mathematics.</li></ul>"""


def feed(title="Quantitative Trading Analyst", employment="Full Time", body=None):
    return f"""<?xml version="1.0"?><rss version="2.0"
    xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
    <title>Careers at Wolverine</title><link>https://wolve.wolve.com/jobs</link>
    <item><title>{escape(title)}</title><link>https://careers.wolve.com/jobs/123</link>
    <guid>https://wolve.wolve.com/jobs/123</guid><pubDate>Wed, 15 Jul 2026 19:13:06 +0100</pubDate>
    <content:encoded>{escape(body if body is not None else content(title, employment))}</content:encoded>
    </item></channel></rss>"""


def parse(text, **options):
    cfg = load_config().companies["wolverine"]
    return parse_feed(text, "wolverine", cfg, PinpointOptions(**(cfg.options | options)))


def test_full_feed_content_preserves_dates_metadata_and_role_without_inference():
    raw = parse(feed())[0]
    assert raw.description == content()
    assert raw.date_posted == datetime(2026, 7, 15, 18, 13, 6, tzinfo=UTC)
    assert raw.location == "Chicago, IL" and raw.employment_type == "Full Time"
    assert raw.external_id == "123" and raw.apply_url == "https://careers.wolve.com/jobs/123"
    assert raw.seniority_hint is None and raw.minimum_experience_years is None
    assert raw.raw_payload == {"department": "Trading"}


@pytest.mark.parametrize(
    "old,new",
    [
        ("Careers at Wolverine", "Careers at Wolverine Worldwide"),
        ("https://careers.wolve.com/jobs/123", "https://evil.example/jobs/123"),
        ("https://careers.wolve.com/jobs/123", "https://careers.wolve.com/jobs/123?apply=1"),
        ("https://wolve.wolve.com/jobs/123", "https://wolve.wolve.com/jobs/124"),
        ("+0100", ""),
        ("Wed, 15 Jul 2026 19:13:06 +0100", "not a date"),
        ("<title>Careers at Wolverine</title>", ""),
        ("</guid>", "</guid><guid>https://wolve.wolve.com/jobs/123</guid>"),
        ("</rss>", ""),
    ],
)
def test_changed_or_ambiguous_feed_rejected(old, new):
    with pytest.raises(SourceUnavailable):
        parse(feed().replace(old, new))


@pytest.mark.parametrize(
    "body",
    [
        "",
        content().replace("<h1>", "<h1 hidden>"),
        content().replace("<strong>Location:", '<strong style="display:none">Location:'),
        content().replace("<strong>Location:", '<strong aria-hidden="true">Location:'),
        content().replace("Chicago, IL", ""),
        content().replace("<h1>Quantitative Trading Analyst</h1>", "<h1>Other title</h1>"),
        content().replace("Location:", "Remote:"),
        content().replace("Full Time", "Unknown"),
    ],
)
def test_description_headers_must_match_visible_publisher_fields(body):
    with pytest.raises(SourceUnavailable):
        parse(feed(body=body))


def test_duplicate_ids_and_feed_limits_abort_the_entire_result():
    text = feed()
    item = text[text.index("<item>") : text.index("</item>") + len("</item>")]
    duplicate = text.replace("</channel>", item + "</channel>")
    with pytest.raises(SourceUnavailable, match="Duplicate"):
        parse(duplicate)
    with pytest.raises(SourceUnavailable, match="result limit"):
        parse(duplicate.replace("/jobs/123</link>", "/jobs/124</link>"), max_results_per_query=1)
    two = text.replace("</channel>", item.replace("/jobs/123", "/jobs/124") + "</channel>")
    with pytest.raises(SourceUnavailable, match="selected-job limit"):
        parse(two, max_details=1)


@pytest.mark.parametrize(
    "text",
    [
        "a" * 2000001,
        '<!DOCTYPE rss [<!ENTITY employer "Wolverine">]>' + feed(),
    ],
    ids=["oversized", "doctype"],
)
def test_xml_resource_expansion_is_not_allowed(text):
    with pytest.raises(SourceUnavailable, match="safe XML"):
        parse(text)


@pytest.mark.parametrize(
    "title", ["Software Engineer", "Trading Operations Analyst", "Trading Summer Analyst"]
)
def test_titles_outside_scope_are_filtered(title):
    assert parse(feed(title)) == []


@pytest.mark.parametrize(
    "title,employment,excluded",
    [
        ("Associate Trader", "Full Time", True),
        ("Analyst / Associate Trader", "Full Time", False),
        ("Quantitative Trading Analyst", "Internship", True),
    ],
)
def test_existing_associate_and_internship_policy_still_applies(title, employment, excluded):
    raw = parse(feed(title, employment))[0]
    job = score_job(normalize(raw), load_config().keywords)
    assert bool(job.score_breakdown.exclusions) == excluded


@pytest.mark.parametrize("status", [200, 403, 500])
def test_collector_only_fetches_public_feed_and_never_claims_complete_coverage(status):
    cfg = load_config().companies["wolverine"].model_copy(deep=True)
    cfg.request_interval = 0.1
    urls = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        urls.append(str(request.url))
        return httpx.Response(status, text=feed())

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            collector = build_collector("wolverine", cfg, http)
            if status == 200:
                result = await collector.collect()
                assert len(result.jobs) == 1 and not result.complete
            else:
                with pytest.raises(SourceUnavailable):
                    await collector.collect()
        finally:
            await http.close()

    asyncio.run(run())
    assert urls == [FEED]


def test_timeout_and_unverified_tenant_fail_closed(monkeypatch):
    cfg = load_config().companies["wolverine"].model_copy(deep=True)

    async def run():
        http = HTTPClient(retries=0)

        async def slow(*args, **kwargs):
            raise TimeoutError

        monkeypatch.setattr(http, "get_text", slow)
        try:
            with pytest.raises(SourceUnavailable, match="time budget"):
                await build_collector("wolverine", cfg, http).collect()
            cfg.tenant = "other"
            with pytest.raises(ValueError, match="verified"):
                build_collector("wolverine", cfg, http)
        finally:
            await http.close()

    asyncio.run(run())
