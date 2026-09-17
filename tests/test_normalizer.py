from datetime import UTC, datetime

import pytest

from trading_radar.normalizer import (
    canonical_url,
    company_key,
    location_parts,
    normalize,
    parse_date,
    plain_text,
)


@pytest.mark.parametrize("value", ["Société Générale", "Societe Generale", "SG CIB"])
def test_company_aliases(value):
    assert company_key(value) == "societe generale"


@pytest.mark.parametrize("value", ["J.P. Morgan", "JPMorgan Chase", "JPMorgan"])
def test_jpmorgan_aliases(value):
    assert company_key(value) == "jpmorgan"


def test_locations():
    assert location_parts("Greater London")[0] == "London, UK"
    assert location_parts("London, England, United Kingdom")[0] == "London, UK"
    assert location_parts("Frankfurt am Main")[0] == "Frankfurt, DE"
    assert location_parts("London / Paris")[1] is None


def test_url_cleanup():
    assert (
        canonical_url("https://example.com/jobs/?id=2&utm_source=x#top")
        == "https://example.com/jobs?id=2"
    )
    assert canonical_url("https://example.com/?gh_jid=42") == "https://example.com?gh_jid=42"
    assert canonical_url("https://example.com/careers#/jobs/42").endswith("#/jobs/42")


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "file:///etc/passwd", "https://user:password@example.com", "bad"]
)
def test_bad_urls_rejected(url):
    with pytest.raises(ValueError):
        canonical_url(url)


def test_dates():
    now = datetime(2026, 9, 15, tzinfo=UTC)
    assert parse_date("2 days ago", now).day == 13
    assert parse_date("15 September 2026") == now
    assert parse_date("2026-09-15T02:00:00+02:00") == now
    assert parse_date("01/02/2027") is None
    assert parse_date("unknown") is None


def test_html():
    assert (
        plain_text("<p>FX</p><script>bad()</script><p>Trader &amp; Analyst</p>")
        == "FX Trader & Analyst"
    )


def test_identity_stable_when_title_changes(raw):
    first = normalize(raw)
    raw.title = "New title"
    assert normalize(raw).fingerprint == first.fingerprint


def test_source_ids_are_namespaced(raw):
    first = normalize(raw)
    raw.source = "different"
    assert normalize(raw).fingerprint != first.fingerprint
