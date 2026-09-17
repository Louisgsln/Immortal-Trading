import asyncio
import html
import json

import httpx
import pytest

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.ubs import (
    BOARD,
    PROFESSIONAL_BOARD,
    UBSCollector,
    detail_url,
    page_data,
    parse_detail,
)


def config(**options):
    return Company(name="UBS", ats="ubs", career_url=BOARD, request_interval=0.1, options=options)


def page(data, bootstrap=False):
    result = '<input id="preLoadJSON" value="' + html.escape(json.dumps(data), quote=True) + '">'
    if bootstrap:
        result += '<input id="partnerId" value="25008"><input id="siteId" value="5131"><input id="linkId" value="15232"><input id="CookieValue" value="synthetic-anonymous-session">'
    return result


def bootstrap():
    return page(
        {
            "ShowCaptcha": False,
            "SmartSearchJSONValue": json.dumps(
                {"KeywordCustomSolrFields": "JobTitle", "LocationCustomSolrFields": "Location"}
            ),
        },
        True,
    )


def url(i):
    return f"https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5131&PageType=JobDetails&jobid={i}"


def listing(i="123", title="2027 Graduate Global Markets"):
    return {
        "Questions": [
            {"QuestionName": "reqid", "Value": i},
            {"QuestionName": "jobtitle", "Value": title},
        ],
        "Link": url(i),
        "IsActive": False,
    }


def detail(i="123", **changes):
    return {
        "Jobdetails": {
            "isActive": True,
            "Link": url(i),
            "JobDetailQuestions": [
                {"VerityZone": "reqid", "AnswerValue": i},
                {"VerityZone": "jobtitle", "AnswerValue": "2027 Graduate Global Markets"},
                {"VerityZone": "formtext2", "AnswerValue": "London"},
                {"VerityZone": "formtext23", "AnswerValue": "United Kingdom"},
                {
                    "VerityZone": "jobdescription",
                    "AnswerValue": "Trade rates",
                    "QuestionName": "Your role",
                    "QuestionType": "textarea",
                },
                {
                    "VerityZone": "formtext59",
                    "AnswerValue": "Python, 0-2 years",
                    "QuestionName": "Your expertise",
                    "QuestionType": "textarea",
                },
                {"VerityZone": "lastupdated", "AnswerValue": "16-Sep-2026"},
            ],
            **changes,
        }
    }


def execute(handler, monkeypatch, **options):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await UBSCollector("ubs", config(**options), http).collect()
        finally:
            await http.close()

    return asyncio.run(run())


def test_anonymous_pagination_all_descriptions_and_no_session_storage(monkeypatch):
    pages = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method == "POST":
            body = json.loads(req.content)
            pages.append(body["pageNumber"])
            assert (
                body["keyword"] == ""
                and body["encryptedSessionValue"] == "synthetic-anonymous-session"
            )
            rows = (
                [listing(), listing("124", "Graduate Operations")]
                if body["pageNumber"] == 1
                else [listing("125", "Graduate Operations")]
            )
            return httpx.Response(200, json={"JobsCount": 3, "PageSize": 2, "Jobs": {"Job": rows}})
        if req.url.params.get("PageType") == "JobDetails":
            return httpx.Response(200, text=page(detail()))
        return httpx.Response(200, text=bootstrap())

    result = execute(handler, monkeypatch)
    assert pages == [1, 2] and len(result.jobs) == 1 and not result.complete
    job = result.jobs[0]
    assert (
        "Your role" in job.description
        and "Your expertise" in job.description
        and "Python" in job.description
    )
    assert job.location == "London, United Kingdom" and job.external_id == "123"
    assert job.date_posted is None and job.expected_start_date is None
    assert "synthetic-anonymous-session" not in job.model_dump_json()


@pytest.mark.parametrize(
    "response,match",
    [
        ({"JobsCount": 2, "PageSize": 50, "Jobs": {"Job": [listing()]}}, "short"),
        ({"JobsCount": 2, "PageSize": 50, "Jobs": {"Job": [listing(), listing()]}}, "repeated"),
        ({"JobsCount": 2000, "PageSize": 50, "Jobs": {"Job": []}}, "limit"),
        ({"JobsCount": 1, "PageSize": None, "Jobs": {"Job": [listing()]}}, "metadata"),
        (
            {"JobsCount": 1, "PageSize": 50, "Jobs": {"Job": [{"Questions": [], "Link": url(1)}]}},
            "identifier",
        ),
    ],
)
def test_bad_search_aborts(monkeypatch, response, match):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        return (
            httpx.Response(200, json=response)
            if req.method == "POST"
            else httpx.Response(200, text=bootstrap())
        )

    with pytest.raises(SourceUnavailable, match=match):
        execute(handler, monkeypatch)


@pytest.mark.parametrize(
    "body",
    [
        "<html>Blocked</html>",
        page({"ShowCaptcha": True}),
        '<input id="preLoadJSON" value="broken">',
    ],
)
def test_missing_bootstrap_or_challenge(body):
    with pytest.raises(SourceUnavailable):
        page_data(body)


@pytest.mark.parametrize(
    "value",
    [
        "https://evil.example/jobs/123",
        url(123).replace("25008", "999"),
        url(123) + "&token=x",
        url(123) + "&jobid=999",
        url(123).replace("https:", "http:"),
    ],
)
def test_only_public_ubs_detail_urls(value):
    with pytest.raises(SourceUnavailable):
        detail_url(value, "123")


def test_locale_link_preserves_verified_origin_site():
    link = url(123).replace("siteid=5131", "siteid=5132") + "&frmSiteId=5131"
    assert detail_url(link, "123") == link
    with pytest.raises(SourceUnavailable):
        detail_url(link.replace("frmSiteId=5131", "frmSiteId=999"), "123")


def test_detail_identity_missing_fields_and_inactive():
    with pytest.raises(SourceUnavailable):
        parse_detail(detail("456"), {"reqid": "123"}, config(), "ubs")
    with pytest.raises(SourceUnavailable):
        parse_detail(detail(JobDetailQuestions=[]), {"reqid": "123"}, config(), "ubs")
    assert parse_detail(detail(isActive=False), {"reqid": "123"}, config(), "ubs") is None


def test_access_denied_is_not_retried(monkeypatch):
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(403)

    with pytest.raises(SourceUnavailable, match="403"):
        execute(handler, monkeypatch)
    assert len(calls) == 1


def test_reject_unsupported_search_terms():
    with pytest.raises(ValueError):
        UBSCollector("ubs", config(search_terms=["trading"]), None)


def test_changed_total_and_detail_limit(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method != "POST":
            return httpx.Response(200, text=bootstrap())
        number = json.loads(req.content)["pageNumber"]
        return httpx.Response(
            200,
            json={
                "JobsCount": 2 if number == 1 else 3,
                "PageSize": 1,
                "Jobs": {"Job": [listing(str(number))]},
            },
        )

    with pytest.raises(SourceUnavailable, match="changed"):
        execute(handler, monkeypatch)

    def limit(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method != "POST":
            return httpx.Response(200, text=bootstrap())
        return httpx.Response(
            200, json={"JobsCount": 2, "PageSize": 50, "Jobs": {"Job": [listing(), listing("124")]}}
        )

    with pytest.raises(SourceUnavailable, match="detail limit"):
        execute(limit, monkeypatch, max_details=1)


def test_zero_page_size_means_ui_default_fifty(monkeypatch):
    numbers = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method != "POST":
            return httpx.Response(200, text=bootstrap())
        number = json.loads(req.content)["pageNumber"]
        numbers.append(number)
        rows = [
            listing(str(i), "Graduate Operations")
            for i in range((number - 1) * 50, min(number * 50, 51))
        ]
        return httpx.Response(200, json={"JobsCount": 51, "PageSize": 0, "Jobs": {"Job": rows}})

    assert not execute(handler, monkeypatch).jobs
    assert numbers == [1, 2]


@pytest.mark.parametrize("wrong_context", [None, "siteId", "linkId", "partnerId"])
def test_professional_board_uses_separate_bootstrap(monkeypatch, wrong_context):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    calls = []

    def handler(req):
        calls.append(req)
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.method == "POST":
            body = json.loads(req.content)
            assert body["siteId"] == "5012" and body["linkId"] == "15231"
            assert body["keyword"] == ""
            item = listing()
            item["Link"] = url(123).replace("5131", "5012") + "&frmSiteId=5012"
            return httpx.Response(
                200, json={"JobsCount": 1, "PageSize": 50, "Jobs": {"Job": [item]}}
            )
        if req.url.params.get("PageType") == "JobDetails":
            data = detail()
            data["Jobdetails"]["Link"] = url(123).replace("5131", "5012")
            return httpx.Response(200, text=page(data))
        assert str(req.url) == PROFESSIONAL_BOARD
        text = bootstrap().replace("5131", "5012").replace("15232", "15231")
        if wrong_context:
            text = text.replace(f'id="{wrong_context}" value="', f'id="{wrong_context}" value="999')
        return httpx.Response(200, text=text)

    async def run():
        http = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            cfg = config().model_copy(update={"career_url": PROFESSIONAL_BOARD})
            return await UBSCollector("ubs_professionals", cfg, http).collect()
        finally:
            await http.close()

    if wrong_context:
        with pytest.raises(SourceUnavailable, match="context"):
            asyncio.run(run())
        assert len(calls) == 2
    else:
        result = asyncio.run(run())
        assert len(result.jobs) == 1 and not result.complete
        assert result.jobs[0].source == "ubs_professionals"
        assert result.jobs[0].seniority_hint is None
        assert "synthetic-anonymous-session" not in result.model_dump_json()


def test_professional_localized_link_checks_origin():
    link = url(123).replace("5131", "5013") + "&frmSiteId=5012"
    assert detail_url(link, "123", "5012") == link
    with pytest.raises(SourceUnavailable, match="URL"):
        detail_url(link.replace("frmSiteId=5012", "frmSiteId=5131"), "123", "5012")


@pytest.mark.parametrize(
    "changes", [{"name": "Other"}, {"career_url": PROFESSIONAL_BOARD + "&extra=x"}]
)
def test_unverified_professional_configuration_rejected(changes):
    with pytest.raises(ValueError, match="verified UBS"):
        UBSCollector("ubs_professionals", config().model_copy(update=changes), None)
