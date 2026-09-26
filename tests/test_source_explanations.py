import asyncio
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from trading_radar.health import check_health
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.runtime_status import format_status
from trading_radar.source_failure import failure_summary

NOW = datetime(2026, 9, 26, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    "error,code",
    [
        ("Nomura campus access restricted: CAPTCHA challenge; retry later", "captcha"),
        ("Nomura campus CAPTCHA session expired; renewal required", "captcha"),
        ("robots policy disallows this endpoint", "robots_denied"),
        ("access restricted: HTTP 403", "access_restricted"),
        ("HTTP 429 after retries", "rate_limited"),
        ("server requests a later retry; deferring source", "rate_limited"),
        ("Macquarie public portal error page", "portal_error"),
        ("HTTP 503 after retries", "portal_error"),
        ("HTTP 302", "redirect"),
        ("network timeout or transport error", "timeout"),
        ("Source time budget exceeded", "timeout"),
        ("UBS repeated page", "pagination"),
        ("Macquarie total changed during pagination", "pagination"),
        ("Macquarie result count missing", "format_changed"),
        ("secret=https://user:password@example.test/path", "unavailable"),
        (None, "unavailable"),
    ],
)
def test_bounded_public_explanation(error, code):
    summary = failure_summary(error)
    assert summary["code"] == code
    assert len(summary["label"]) < 100
    assert not any(token in summary["label"] for token in ["secret", "password", "http", "example"])


def prepare(config, repo, failures=1, error="HTTP 302", success=None):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    with repo.transaction():
        repo.db.execute(
            "INSERT INTO companies(source,last_success,last_failure,consecutive_failures) VALUES(?,?,?,?)",
            ("test", success or (NOW - timedelta(hours=1)).isoformat(), NOW.isoformat(), failures),
        )
        repo.db.execute(
            "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)",
            (NOW.isoformat(), json.dumps({"failed": {"test": error}})),
        )


@pytest.mark.parametrize(
    "failures,seconds", [(1, 600), (2, 1200), (3, 2400), (4, 3600), (100, 3600)]
)
def test_health_shows_backoff_without_claiming_future_success(config, repo, failures, seconds):
    prepare(config, repo, failures)
    before = list(repo.db.iterdump())
    source = check_health(config, now=NOW)["sources"][0]
    assert source["status"] == "recent_failure"
    assert source["failure"]["code"] == "redirect"
    assert source["schedule"] == {
        "interval_seconds": 300,
        "cooldown_seconds": seconds,
        "next_eligible_at": (NOW + timedelta(seconds=seconds)).isoformat(),
        "eligible_now": False,
    }
    assert check_health(config, now=NOW + timedelta(seconds=seconds))["sources"][0]["schedule"][
        "eligible_now"
    ]
    assert list(repo.db.iterdump()) == before


def test_old_failure_disappears_after_success(config, repo):
    prepare(config, repo)
    with repo.transaction():
        repo.db.execute(
            "UPDATE companies SET last_success=?,consecutive_failures=0",
            ((NOW + timedelta(minutes=1)).isoformat(),),
        )
    source = check_health(config, now=NOW + timedelta(minutes=2))["sources"][0]
    assert source["failure"] is None and source["schedule"]["cooldown_seconds"] == 300
    assert source["schedule"]["next_eligible_at"] == (NOW + timedelta(minutes=6)).isoformat()


def test_unstarted_and_invalid_sources_have_no_invented_schedule(config, repo):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    source = check_health(config, now=NOW)["sources"][0]
    assert source["schedule"]["next_eligible_at"] is None and source["schedule"]["eligible_now"]
    prepare(config, repo, success="broken")
    source = check_health(config, now=NOW)["sources"][0]
    assert (
        source["schedule"]["next_eligible_at"] is None
        and source["schedule"]["eligible_now"] is None
    )
    assert source["failure"] is None


def test_telegram_status_uses_sanitized_reason_and_possible_retry(config, repo):
    prepare(config, repo, error="Macquarie public portal error page")
    report = {
        "health": check_health(config, now=NOW),
        "watcher": {"status": "active", "at": None},
        "deliveries": {},
        "alerts_enabled": True,
        "threshold": 70,
    }
    text = format_status(report)
    assert "page d’erreur" in text and "Reprise possible dès" in text
    assert "http" not in text and len(text.encode("utf-16-le")) // 2 < 4096


@pytest.mark.parametrize(
    "location,expected",
    [
        ("/en_US/careers/Error", "Macquarie public portal error page"),
        (
            "https://recruitment.macquarie.com/en_US/careers/Error",
            "Macquarie public portal error page",
        ),
        ("https://evil.test/en_US/careers/Error", "HTTP 302"),
        ("/en_US/careers/Error?private=secret", "HTTP 302"),
        ("/en_US/careers/SearchJobs/", "HTTP 302"),
    ],
)
def test_macquarie_error_redirect_never_followed(location, expected):
    seen = []

    def response(request):
        seen.append(request.url.path)
        return (
            httpx.Response(404)
            if request.url.path == "/robots.txt"
            else httpx.Response(302, headers={"Location": location})
        )

    async def run():
        client = HTTPClient(transport=httpx.MockTransport(response))
        try:
            with pytest.raises(SourceUnavailable, match=expected):
                await client.get_text(
                    "https://recruitment.macquarie.com/en_US/careers/SearchJobs/", 0, "test"
                )
        finally:
            await client.close()

    asyncio.run(run())
    assert seen == ["/robots.txt", "/en_US/careers/SearchJobs/"]
