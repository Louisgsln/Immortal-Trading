import asyncio
import json

import httpx
import pytest

from scripts import probe_source_fields as fields
from tests.test_ca_cib import card as ca_card
from tests.test_ca_cib import config as ca_config
from tests.test_ca_cib import detail as ca_detail
from tests.test_ca_cib import listing as ca_listing
from tests.test_greenhouse_filtered import config as imc_config
from tests.test_greenhouse_filtered import row as imc_row
from tests.test_hsbc import config as hsbc_config
from tests.test_hsbc import detail as hsbc_detail
from tests.test_hsbc import listing as hsbc_listing
from tests.test_sig import config as sig_config
from tests.test_sig import page as sig_page
from tests.test_sig import row as sig_row
from trading_radar.http import SourceUnavailable


@pytest.fixture
def no_side_effects(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Diagnostic must not use a database, notifier, service or shell")

    async def no_sleep(_):
        pass

    monkeypatch.setattr("sqlite3.connect", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("trading_radar.notifications.TelegramNotifier.from_env", forbidden)
    monkeypatch.setattr("trading_radar.notifications.TelegramNotifier.send_text", forbidden)
    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:fixture_private_token_not_to_print")


def execute(source, config, handler):
    async def run():
        http = fields.ProbeHTTP(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await fields.probe(source, config, http)
        finally:
            await http.close()

    return asyncio.run(run())


@pytest.mark.parametrize("source", ["imc", "credit_agricole_cib", "hsbc_graduates", "sig"])
def test_public_probe_reports_failed_field_without_database_notifier_or_service_use(
    source, config, no_side_effects, monkeypatch
):
    monkeypatch.setattr(fields.sig, "PAGE_SIZE", 2)
    companies = {
        "imc": imc_config(),
        "credit_agricole_cib": ca_config(),
        "hsbc_graduates": hsbc_config(),
        "sig": sig_config(),
    }
    config.companies = companies
    config.settings.alerts_enabled = True
    config.settings.telegram_control_enabled = True
    module, name = fields.SOURCES[source]
    before = getattr(module, name)

    def handler(request):
        assert request.method == "GET"
        assert request.url.host in fields.HOSTS
        assert not any(k in request.headers for k in ("authorization", "cookie"))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if source == "imc":
            row = imc_row(
                metadata=[
                    {"name": "Is Hidden Job?", "value": None},
                    {"name": "Worker Sub Type", "value": "New Unverified Level"},
                ]
            )
            return httpx.Response(200, json={"meta": {"total": 1}, "jobs": [row]})
        if source == "credit_agricole_cib":
            return httpx.Response(
                200,
                text=ca_listing([ca_card()])
                if request.url.path.endswith("listeoffre.aspx")
                else ca_detail(fldjobdescription_date1="31/02/2027"),
            )
        if source == "hsbc_graduates":
            return httpx.Response(
                200,
                text=hsbc_listing(total=1)
                if request.url.path.endswith("find-a-programme")
                else hsbc_detail().replace("addressLocality", "addressRegion"),
            )
        return httpx.Response(200, json=sig_page([sig_row(1), sig_row(2)], 4))

    report = execute(source, config, handler)
    assert report["status"] == "failed"
    assert getattr(module, name) is before
    assert "fixture_private_token" not in json.dumps(report)
    if source == "imc":
        assert report["samples"][0]["worker_sub_type"] == "New Unverified Level"
        assert report["samples"][0]["field_present"] is True
    elif source == "credit_agricole_cib":
        assert report["samples"][0]["value"] == "31/02/2027"
        assert report["validation_check"] == "invalid CA CIB employment start date"
    elif source == "hsbc_graduates":
        assert report["validation_check"] == "HSBC incomplete address"
        assert report["samples"][0]["fields"][1]["value"] == "FR"
    else:
        assert report["validation_check"] == "SIG duplicate jobs or repeated page"
        # The helper also runs with lot 103, whose collector does not retry.
        assert [p["page"] for p in report["pages"]] in ([1, 2], [1, 2, 1, 2])
        assert report["pages"][0]["first_ids"] == ["1", "2"]


def test_transport_refusal_keeps_error_and_request_url_private(config, no_side_effects):
    config.companies = {"imc": imc_config()}

    def handler(request):
        return (
            httpx.Response(404)
            if request.url.path == "/robots.txt"
            else httpx.Response(403, text="fixture_private_token")
        )

    report = execute("imc", config, handler)
    assert report["http_status"] == 403
    assert report["failure"]["code"] == "access_restricted"
    assert report["samples"] == []
    assert "fixture_private_token" not in json.dumps(report)
    assert "https://" not in json.dumps(report)


@pytest.mark.parametrize(
    "url,method",
    [
        ("https://api.telegram.org/private", "GET"),
        ("https://careers.sig.com/account/login", "GET"),
        ("https://apply.careers.hsbc.com/talentcommunity/apply/123/", "GET"),
        ("https://careers.sig.com/api/jobs", "POST"),
        ("http://careers.sig.com/api/jobs", "GET"),
        ("https://username:password@careers.sig.com/api/jobs", "GET"),
    ],
)
def test_probe_scope_refuses_private_accounts_other_hosts_and_non_get_requests(url, method):
    def forbidden(request):
        pytest.fail("Refused request reached the transport")

    async def run():
        http = fields.ProbeHTTP(transport=httpx.MockTransport(forbidden), retries=0)
        try:
            with pytest.raises(SourceUnavailable, match="scope rejected"):
                await http._request(url, 1, "sig", method=method)
        finally:
            await http.close()

    asyncio.run(run())


def test_request_budget_is_bounded_and_robots_policy_is_respected(no_side_effects):
    async def run():
        http = fields.ProbeHTTP(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, text="User-agent: *\nDisallow: /api/jobs")
            ),
            retries=0,
        )
        try:
            with pytest.raises(SourceUnavailable, match="robots policy disallows"):
                await http.get_json("https://careers.sig.com/api/jobs", 1, "sig")
            assert http.counts["sig"] == 1
            http.counts["sig"] = 40
            with pytest.raises(SourceUnavailable, match="request budget"):
                await http._request("https://careers.sig.com/api/jobs", 1, "sig")
        finally:
            await http.close()

    asyncio.run(run())


def test_diagnostic_fields_redact_urls_emails_and_credential_shapes():
    text = "ASAP https://example.com/private person@example.com 123456:abcdefghijklmnopqrstuvwxyz"
    result = fields.bounded(text)
    assert result == "ASAP [masque] [masque] [masque]"
    assert fields.bounded({"unexpected": "secret"}) == {"type": "dict"}


def test_probe_limit_is_distinguished_from_employer_failure(config, no_side_effects):
    config.companies = {"imc": imc_config()}

    async def run():
        http = fields.ProbeHTTP(
            transport=httpx.MockTransport(lambda _: pytest.fail("No request permitted")), retries=0
        )
        http.counts["imc"] = 40
        try:
            return await fields.probe("imc", config, http)
        finally:
            await http.close()

    report = asyncio.run(run())
    assert report["status"] == "diagnostic_limit"
    assert report["limit"] == "requests"
    assert "failure" not in report
