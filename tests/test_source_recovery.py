import asyncio
import json
from collections import defaultdict

import httpx
import pytest

from trading_radar.bnp import SEARCH, BNPCollector
from trading_radar.bnp_authority import matching_alias, recruitment_target
from trading_radar.config import Company
from trading_radar.health import check_health
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, CollectionConflict
from trading_radar.runtime_status import format_status
from trading_radar.scan_preview import preview_scan
from trading_radar.scanner import scan
from trading_radar.workday import WorkdayCollector


def authority(ref="REF1", title="Trading Analyst", description="Trade bonds", identifier="123"):
    return f"""<link rel="canonical" href="https://bwelcome.hr.bnpparibas/en_US/externalcareers/JobDetail/Trading/{identifier}">
    <h1 class="title--banner">{title}</h1>
    <div class="article__content__view__field"><div class="article__content__view__field__label">Ref #</div>
    <div class="article__content__view__field__value">{ref}</div></div>
    <article><h2>Description</h2><div class="article__content">{description}</div></article>"""


def aliases(raw):
    good = raw.model_copy(
        update={
            "external_id": "REF1",
            "title": "Trading Analyst",
            "description": "<p>Trade bonds</p>",
        }
    )
    bad = good.model_copy(
        update={"description": "Trade equities", "apply_url": good.apply_url + "-old"}
    )
    return [bad, good]


def test_bnp_requires_unique_exact_official_title_description_and_reference(raw):
    candidates = aliases(raw)
    before = [j.model_dump() for j in candidates]
    assert matching_alias(authority(), "123", candidates) is candidates[1]
    assert matching_alias(authority(description="Trade  bonds"), "123", candidates) is candidates[1]
    assert [j.model_dump() for j in candidates] == before
    assert matching_alias(authority(), "123", candidates + [candidates[1]]) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"ref": "OTHER"},
        {"identifier": "456"},
        {"title": "Senior Trading Analyst"},
        {"description": "Trade bonds unless limits are exceeded"},
        {"description": ""},
    ],
)
def test_bnp_authority_disagreement_stays_quarantined(raw, changes):
    assert matching_alias(authority(**changes), "123", aliases(raw)) is None


@pytest.mark.parametrize(
    "transform",
    [
        lambda s: s.replace("bwelcome.hr.bnpparibas", "evil.example"),
        lambda s: s.replace("https:", "http:"),
        lambda s: s + '<h1 class="title--banner">Trading Analyst</h1>',
        lambda s: (
            s
            + '<article><h2>Description</h2><div class="article__content">Trade bonds</div></article>'
        ),
        lambda s: s.replace('class="article__content"', 'class="changed"'),
        lambda s: s.replace('rel="canonical"', 'rel="other"'),
    ],
)
def test_bnp_unrecognized_or_ambiguous_authority_is_not_used(raw, transform):
    assert matching_alias(transform(authority()), "123", aliases(raw)) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/en_US/externalcareers/JobDetails?jobId=123",
        "https://bwelcome.hr.bnpparibas/en_US/externalcareers/JobDetails?jobId=123&token=secret",
        "https://bwelcome.hr.bnpparibas/en_US/externalcareers/JobDetails?jobId=123&jobId=456",
        "https://bwelcome.hr.bnpparibas/en_US/externalcareers/JobDetails?jobId=abc",
        "https://bwelcome.hr.bnpparibas/en_US/externalcareers/JobDetails?jobId=123#section",
    ],
)
def test_bnp_untrusted_target_does_not_trigger_fetch(url):
    assert recruitment_target(f'<a href="{url}">Postuler</a>') is None


def test_bnp_target_duplicates_and_conflicting_targets():
    url = "https://bwelcome.hr.bnpparibas/en_US/externalcareers/JobDetails?jobId=123&source=BNP+Paribas+website"
    link = f'<a href="{url}">Postuler</a>'
    assert recruitment_target(link * 2) == ("123", url)
    assert recruitment_target(link + link.replace("123", "456")) is None
    assert recruitment_target("<p>No application link</p>") is None


def workday(monkeypatch, rows, source="deutsche_bank", total=None):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    cfg = Company(
        name="Test",
        ats="workday",
        career_url="https://demo.wd3.myworkdayjobs.com/External",
        request_interval=0.1,
    )
    calls = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert request.method == "POST"
        offset = json.loads(request.content)["offset"]
        calls.append(offset)
        return httpx.Response(
            200,
            json={
                "total": len(rows) if total is None else total,
                "jobPostings": rows[offset : offset + 20],
            },
        )

    async def run():
        h = HTTPClient(retries=0, transport=httpx.MockTransport(handler))
        try:
            return await WorkdayCollector(source, cfg, h).collect()
        finally:
            await h.close()

    return asyncio.run(run()), calls


@pytest.mark.parametrize(("source", "ref"), [("deutsche_bank", "R0427551"), ("citi", "26988331")])
def test_workday_reference_only_placeholder_is_counted_and_reported(monkeypatch, source, ref):
    rows = [{"title": "Operations", "externalPath": f"/job/Paris/{i}"} for i in range(22)]
    rows.insert(13, {"bulletFields": [ref]})
    result, offsets = workday(monkeypatch, rows, source)
    assert offsets == [0, 20] and not result.jobs and not result.complete
    assert result.listing_gaps == [ref]


@pytest.mark.parametrize(
    "row",
    [
        {},
        {"bulletFields": []},
        {"bulletFields": [123]},
        {"bulletFields": ["R1"]},
        {"bulletFields": ["R0427551", "R0000001"]},
        {"bulletFields": ["R0427551"], "title": None},
        {"bulletFields": ["R0427551"], "externalPath": "//evil.example"},
    ],
)
def test_workday_other_malformed_listings_still_fail(monkeypatch, row):
    with pytest.raises(SourceUnavailable):
        workday(monkeypatch, [row])


def test_workday_placeholder_limits_duplicates_and_unknown_sources(monkeypatch):
    with pytest.raises(SourceUnavailable, match="repeated"):
        workday(monkeypatch, [{"bulletFields": ["R0427551"]}] * 2)
    with pytest.raises(SourceUnavailable, match="limit"):
        workday(monkeypatch, [{"bulletFields": [f"R{i:07d}"]} for i in range(11)])
    with pytest.raises(SourceUnavailable, match="malformed"):
        workday(monkeypatch, [{"bulletFields": ["R0427551"]}], "other")


class Snapshot:
    def __init__(self, jobs, gaps=(), error=None):
        self.result = Collection(jobs=jobs, listing_gaps=list(gaps), complete=True)
        self.error = error

    async def collect(self):
        if self.error:
            raise SourceUnavailable(self.error)
        return self.result


def test_partial_scan_updates_valid_jobs_keeps_absent_jobs_and_clears_on_recovery(
    config, repo, raw
):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )

    def run(snapshot):
        return asyncio.run(scan(config, repo, collectors={"test": snapshot}))

    run(Snapshot([raw]))
    other = raw.model_copy(
        update={
            "external_id": "OTHER",
            "title": "Rates Trading Analyst",
            "apply_url": raw.apply_url + "-other",
        }
    )
    for _ in range(3):
        result = run(Snapshot([other], ["R0427551"]))
        assert result.listing_gaps == {"test": ["R0427551"]}
        assert not result.failed and result.closed == 0
    assert all(j.is_active for j in repo.list_jobs())
    report = check_health(config)
    assert report["sources"][0]["status"] == "partial"
    assert report["sources"][0]["listing_gaps"] == ["R0427551"]
    assert report["source_summary"] == {"partial": 1}
    run(Snapshot([raw, other]))
    assert check_health(config)["source_summary"] == {"fresh": 1}


def test_nomura_restriction_is_explicit_and_recovers(config, repo):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    config.companies = {"nomura_campus": Company(name="Nomura", ats="fixture", enabled=True)}
    error = "Nomura campus access restricted: CAPTCHA challenge; retry later"
    asyncio.run(scan(config, repo, collectors={"nomura_campus": Snapshot([], error=error)}))
    health = check_health(config)
    assert health["source_summary"] == {"access_restricted": 1}
    text = format_status(
        {
            "health": health,
            "watcher": {"status": "active", "at": None},
            "deliveries": {},
            "alerts_enabled": True,
            "threshold": 70,
        }
    )
    assert "accès bloqué par CAPTCHA" in text and "jamais collectée" not in text
    asyncio.run(scan(config, repo, collectors={"nomura_campus": Snapshot([])}))
    assert check_health(config)["source_summary"] == {"fresh": 1}


@pytest.mark.parametrize("broken", [False, True])
def test_bnp_conflict_resolution_fetches_shared_authority_or_retains_conflict(monkeypatch, broken):
    urls = [
        "https://group.bnpparibas/emploi-carriere/offre-emploi/job-1",
        "https://group.bnpparibas/emploi-carriere/offre-emploi/job-2",
    ]
    target = "https://bwelcome.hr.bnpparibas/en_US/externalcareers/JobDetails?jobId=123"
    pages = {}
    for index, url in enumerate(urls):
        record = {
            "@type": "JobPosting",
            "identifier": {"value": "REF1"},
            "title": "Trading Analyst",
            "description": "Trade bonds" if index == 0 else "Trade equities",
            "url": url,
            "jobLocation": {"address": {"addressLocality": "Paris", "addressCountry": "FR"}},
        }
        pages[url] = (
            '<script type="application/ld+json">'
            + json.dumps(record)
            + "</script>"
            + f'<a href="{target}">Postuler</a>'
        )

    class FakeHTTP:
        counts = defaultdict(int)

        async def get_text(self, url, interval, source):
            self.counts[source] += 1
            if url == target:
                if broken:
                    raise SourceUnavailable("access restricted: HTTP 403")
                return authority()
            return pages[url]

    cfg = Company(name="BNP", ats="bnp", career_url=SEARCH)
    collector = BNPCollector("bnp", cfg, FakeHTTP())

    async def search(_):
        return {url: {"title": "Trading Analyst"} for url in urls}

    monkeypatch.setattr(collector, "_search", search)
    result = asyncio.run(collector.collect())
    assert result.requests == 3
    if broken:
        assert not result.jobs and result.conflicts[0].external_id == "REF1"
    else:
        assert not result.conflicts and result.jobs[0].apply_url == urls[0]


def test_never_clean_bnp_is_described_as_partial_not_never_collected(config, repo):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    snapshot = Snapshot([])
    snapshot.result.conflicts = [CollectionConflict(external_id="REF1", urls=[], fields=["title"])]
    asyncio.run(scan(config, repo, collectors={"test": snapshot}))
    report = check_health(config)
    assert report["source_summary"] == {"collection_degraded": 1}
    assert repo.state("test")["last_success"] is None


def test_preview_explicitly_reports_incomplete_listings_without_live_writes(config, repo, raw):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    before = list(repo.db.iterdump())
    result = asyncio.run(preview_scan(config, collectors={"test": Snapshot([raw], ["R0427551"])}))
    assert result["status"] == "incomplete"
    assert result["metrics"]["listing_gaps"] == {"test": ["R0427551"]}
    assert list(repo.db.iterdump()) == before
