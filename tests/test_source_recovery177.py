"""Recover current employer regressions without losing tracking or closing unrelated jobs."""

import asyncio
import json
import sqlite3

import httpx
import pytest

from tests import test_hsbc as campus
from tests import test_nomura_professionals as nomura
from tests import test_societe_generale as sg
from tests.test_scanner import FakeNotifier
from trading_radar.hsbc_professionals import BOARD, job_url
from trading_radar.http import HTTPClient, HTTPGone, SourceUnavailable
from trading_radar.models import Collection, CollectionConflict, WithdrawnPosting
from trading_radar.scanner import scan
from trading_radar.withdrawals import FILLED, filled_posting


class Snapshot:
    def __init__(self, jobs=(), withdrawn=(), conflicts=()):
        self.result = Collection(
            jobs=list(jobs),
            withdrawn=list(withdrawn),
            conflicts=list(conflicts),
            scope_complete=True,
        )

    async def collect(self):
        return self.result


def filled(url, message=FILLED):
    return (
        f'<link rel="canonical" href="{url}">'
        '<div class="jobDisplayShell" itemscope="itemscope">'
        f'<div class="job"><p><strong>{message}</strong></p></div></div>'
    )


def withdrawal(job, **changes):
    return WithdrawnPosting(
        **{
            "external_id": job.external_id,
            "apply_url": job.apply_url,
            "evidence": "employer_filled_message",
            **changes,
        }
    )


def run(config, repo, collector, notifier=None):
    return asyncio.run(scan(config, repo, collectors={"test": collector}, notifier=notifier))


@pytest.mark.parametrize(
    "suffix", ["dur%C3%A9e-6-mois", "durée-6-mois", "上海-交易", "d%C3%A9cembre-2026"]
)
def test_hsbc_accented_public_slugs_keep_the_numeric_identity(suffix):
    assert (
        job_url(BOARD + "/job/563774612462815-" + suffix + "?domain=hsbc.com", "563774612462815")
        == BOARD + "/job/563774612462815"
    )


@pytest.mark.parametrize("suffix", ["x%2Fy", "x%5Cy", "x%252fy", "../other", "x%0ay", "x#fragment"])
def test_hsbc_unicode_support_cannot_change_url_scope(suffix):
    with pytest.raises(SourceUnavailable):
        job_url(BOARD + "/job/123-" + suffix, "123")


def test_exact_filled_notice_needs_matching_employer_canonical():
    row = nomura.row(1)
    result = filled_posting(filled(row["url"]), row, nomura.job_url)
    assert result == WithdrawnPosting(
        external_id="1", apply_url=row["url"], evidence="employer_filled_message"
    )
    with pytest.raises(SourceUnavailable, match="identity mismatch"):
        filled_posting(filled(nomura.row(2)["url"]), row, nomura.job_url)
    with pytest.raises(SourceUnavailable):
        filled_posting(filled("https://foreign.example/jobs/1"), row, nomura.job_url)
    with pytest.raises(SourceUnavailable, match="ambiguous"):
        filled_posting(
            filled(row["url"]) + f'<link rel="canonical" href="{row["url"]}">', row, nomura.job_url
        )


@pytest.mark.parametrize(
    "message",
    [
        "Access denied",
        "Complete the CAPTCHA",
        "Job not found",
        "This posting may be filled soon.",
        FILLED + " Trade equities.",
    ],
)
def test_unavailable_or_ambiguous_text_is_never_a_withdrawal(message):
    row = nomura.row()
    assert filled_posting(filled(row["url"], message), row, nomura.job_url) is None


def test_nomura_filled_listing_does_not_block_other_current_roles(monkeypatch):
    rows = [nomura.row(1), nomura.row(2)]

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("/search/"):
            return httpx.Response(200, text=nomura.page(rows))
        return httpx.Response(
            200,
            text=filled(rows[0]["url"]) if req.url.path.endswith("/1/") else nomura.detail(rows[1]),
        )

    result = nomura.execute(handler, monkeypatch)
    assert [j.external_id for j in result.jobs] == ["2"]
    assert [j.external_id for j in result.withdrawn] == ["1"]
    assert result.scope_complete and not result.complete and not result.listing_gaps


def test_hsbc_campus_filled_listing_does_not_block_other_current_programmes(monkeypatch):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("find-a-programme"):
            return httpx.Response(200, text=campus.listing(total=2))
        if req.url.path.endswith("get-programmes"):
            return httpx.Response(200, json=[campus.card(124)])
        if req.url.path.endswith("/123/"):
            return httpx.Response(200, text=filled(campus.url(123, "New-Slug")))
        return httpx.Response(200, text=campus.detail(124))

    result = campus.execute(handler, monkeypatch)
    assert [j.external_id for j in result.jobs] == ["124"]
    assert result.withdrawn[0].external_id == "123"
    assert result.withdrawn[0].apply_url == campus.url(123, "New-Slug")


@pytest.mark.parametrize("status", [404, 410, 403])
def test_sg_only_explicit_gone_status_can_retire_a_listed_role(monkeypatch, status):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if str(req.url) in sg.DIRECTORIES.values():
            lang = "fr" if str(req.url) == sg.DIRECTORIES["fr"] else "en"
            return httpx.Response(
                200, text=sg.listing([sg.card(lang=lang), sg.card("26000DEF", lang=lang)])
            )
        if "26000ABC" in req.url.path:
            return httpx.Response(status)
        return httpx.Response(200, text=sg.detail("26000DEF"))

    if status != 410:
        with pytest.raises(SourceUnavailable):
            sg.execute(handler, monkeypatch)
    else:
        result = sg.execute(handler, monkeypatch)
        assert [j.external_id for j in result.jobs] == ["26000DEF"]
        assert result.withdrawn == [
            WithdrawnPosting(external_id="26000ABC", apply_url=sg.link(), evidence="http_410")
        ]


def test_robots_410_cannot_be_mistaken_for_a_removed_job():
    async def check():
        h = HTTPClient(transport=httpx.MockTransport(lambda req: httpx.Response(410)), retries=0)
        try:
            with pytest.raises(SourceUnavailable, match="robots policy unavailable") as raised:
                await h.get_text("https://example.com/job/1", 0.1, "test")
            assert not isinstance(raised.value, HTTPGone)
        finally:
            await h.close()

    asyncio.run(check())


def test_withdrawal_preserves_job_ids_notes_applications_alerts_and_history(repo, job):
    with repo.transaction():
        repo.upsert(job)
        repo.enqueue(job, "new")
    repo.update_application(job.id, {"status": "Applied", "notes": "Keep my notes"})
    protected = {
        table: [tuple(row) for row in repo.db.execute(f"SELECT * FROM {table}")]
        for table in [
            "applications",
            "application_history",
            "alerts",
            "alert_history",
            "score_history",
        ]
    }
    count_before = repo.db.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0]
    with repo.transaction():
        assert repo.withdraw(job.source, withdrawal(job)) == 1
        assert repo.withdraw(job.source, withdrawal(job)) == 0
    stored = repo.get(job.id)
    assert not stored.is_active and stored.description_text == job.description_text
    assert stored.first_seen == job.first_seen and stored.last_seen == job.last_seen
    assert repo.db.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0] == count_before + 1
    assert (
        repo.db.execute("SELECT event FROM job_versions ORDER BY id DESC LIMIT 1").fetchone()[0]
        == "closed"
    )
    assert protected == {
        table: [tuple(row) for row in repo.db.execute(f"SELECT * FROM {table}")]
        for table in protected
    }


@pytest.mark.parametrize(
    "changes,source",
    [
        ({"external_id": "unknown"}, "test"),
        ({"apply_url": "https://foreign.example/1"}, "test"),
        ({}, "unrelated"),
    ],
)
def test_unknown_reference_or_url_cannot_close_existing_job(repo, job, changes, source):
    with repo.transaction():
        repo.upsert(job)
    before = list(repo.db.iterdump())
    with repo.transaction():
        assert repo.withdraw(source, withdrawal(job, **changes)) == 0
    assert list(repo.db.iterdump()) == before


def test_shared_active_alias_survives_withdrawal_and_confirmed_job_can_reopen(repo, job):
    alias = job.model_copy(update={"source": "second", "external_id": "second-id"})
    with repo.transaction():
        repo.upsert(job)
        repo.upsert(alias)
        assert repo.withdraw(job.source, withdrawal(job)) == 0
        assert repo.get(job.id).is_active
        assert repo.withdraw(alias.source, withdrawal(alias)) == 1
        reopened, event = repo.upsert(job)
    assert reopened.id == job.id and event == "reopened" and reopened.is_active


def test_partial_scan_applies_only_explicit_withdrawal_and_keeps_evidence(config, repo, raw):
    config.settings.alerts_enabled = False
    run(config, repo, Snapshot([raw]))
    old = repo.list_jobs()[0]
    new = raw.model_copy(
        update={
            "external_id": "new",
            "apply_url": "https://example.com/jobs/new",
            "title": "Graduate FX Trader 2027",
        }
    )
    result = run(config, repo, Snapshot([new], [withdrawal(old)]))
    assert result.closed == 1 and result.successful == 1 and result.new == 1
    assert not repo.get(old.id).is_active and len(repo.list_jobs()) == 2
    proof = result.source_results["test"]["withdrawn"]
    assert proof == [withdrawal(old).model_dump(mode="json")]
    journal = json.loads(
        repo.db.execute("SELECT metrics FROM scan_runs ORDER BY id DESC").fetchone()[0]
    )
    assert journal["source_results"]["test"]["withdrawn"] == proof
    again = run(config, repo, Snapshot([new], [withdrawal(old)]))
    assert again.closed == again.new == 0


def test_closed_pending_job_is_not_sent(config, repo, raw):
    run(config, repo, Snapshot([raw]))
    job = repo.list_jobs()[0]
    with repo.transaction():
        repo.enqueue(job, "new")
    notifier = FakeNotifier()
    run(config, repo, Snapshot(withdrawn=[withdrawal(job)]), notifier)
    assert not notifier.sent and not repo.pending()
    assert repo.db.execute("SELECT status FROM alerts").fetchone()[0] == "suppressed"


def test_contradictory_snapshot_cannot_close_anything(config, repo, raw):
    run(config, repo, Snapshot([raw]))
    job = repo.list_jobs()[0]
    conflict = CollectionConflict(
        external_id="other", urls=["https://example.com/other"], fields=["title"]
    )
    result = run(config, repo, Snapshot(withdrawn=[withdrawal(job)], conflicts=[conflict]))
    assert result.closed == 0 and repo.get(job.id).is_active
    assert "withdrawn" not in result.source_results["test"]


@pytest.mark.parametrize("overlap", [True, False])
def test_conflicting_withdrawal_identities_abort_before_business_writes(config, repo, raw, overlap):
    run(config, repo, Snapshot([raw]))
    job = repo.list_jobs()[0]
    collector = (
        Snapshot([raw], [withdrawal(job)])
        if overlap
        else Snapshot(withdrawn=[withdrawal(job), withdrawal(job)])
    )
    before = repo.get(job.id).model_dump_json()
    result = run(config, repo, collector)
    assert "test" in result.failed and repo.get(job.id).model_dump_json() == before


def test_failed_transaction_rolls_back_new_jobs_and_withdrawal_together(
    config, repo, raw, monkeypatch
):
    run(config, repo, Snapshot([raw]))
    job = repo.list_jobs()[0]
    new = raw.model_copy(update={"external_id": "new", "apply_url": "https://example.com/jobs/new"})

    def fail(*args):
        raise sqlite3.IntegrityError("synthetic withdrawal failure")

    monkeypatch.setattr(repo, "withdraw", fail)
    result = run(config, repo, Snapshot([new], [withdrawal(job)]))
    assert "test" in result.failed and len(repo.list_jobs()) == 1 and repo.get(job.id).is_active
    assert "withdrawn" not in result.source_results["test"]


def test_empty_withdrawal_does_not_change_historical_collection_contract():
    assert "withdrawn" not in Collection(jobs=[]).model_dump(mode="json")
