import asyncio
from pathlib import Path

import httpx
import pytest

from trading_radar.collectors import build_collector
from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.workable_public import BOARD, detail, listing


def catalogue():
    return Path("tests/fixtures/capula-list132.md").read_text()


def company():
    return Company(
        name="Capula",
        ats="workable_public",
        tenant="capula-investment-management-ltd",
        career_url=BOARD,
        options={"search_terms": [], "title_terms": ["quantitative"]},
    )


def test_real_catalogue_and_full_description_without_inferred_instant():
    rows = listing(catalogue(), 10)
    assert len(rows) == 10
    raw = detail(
        Path("tests/fixtures/capula_credit132.md").read_text(), rows[0], "capula", company()
    )
    assert raw is not None and raw.external_id == "1D78B4440A"
    assert raw.date_posted is None and raw.application_deadline is None
    assert raw.raw_payload["posted_calendar_date"] == "2026-10-05"
    assert "Credit ETFs / Total Return Swaps" in raw.description
    assert raw.apply_url == BOARD + "j/1D78B4440A/apply"


def test_explicitly_speculative_quant_role_is_not_an_open_vacancy():
    assert (
        detail(
            Path("tests/fixtures/capula_quant132.md").read_text(),
            listing(catalogue(), 10)[1],
            "capula",
            company(),
        )
        is None
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("All Open Positions", "Private Positions"),
        ("https://apply.workable.com", "https://evil.test"),
        ("1D78B4440A", "9582487D5F"),
        ("2026-10-05", "2026-99-99"),
    ],
)
def test_catalogue_identity_and_dates_fail_closed(old, new):
    with pytest.raises(SourceUnavailable):
        listing(catalogue().replace(old, new), 10)


def test_missing_catalogue_rows_cannot_close_jobs():
    with pytest.raises(SourceUnavailable):
        listing(catalogue(), 11)


@pytest.mark.parametrize(
    "old,new",
    [
        ("# Credit Quantitative Analyst", "# Other"),
        ("Capula · London", "Capula · Paris"),
        ("## Requirements", "## Other"),
        ("/j/1D78B4440A/apply", "/j/0000000000/apply"),
        ("**Department:** Strategy", "**Department:** Technology"),
    ],
)
def test_detail_identity_and_requirement_changes_fail_closed(old, new):
    text = Path("tests/fixtures/capula_credit132.md").read_text().replace(old, new)
    with pytest.raises(SourceUnavailable):
        detail(text, listing(catalogue(), 10)[0], "capula", company())


@pytest.mark.parametrize("changed", [False, True])
def test_complete_public_list_is_rechecked_before_snapshot(monkeypatch, changed):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)
    reads = []

    def handler(req):
        reads.append(req.url.path)
        assert req.method == "GET"
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path.endswith("/llms.txt"):
            return httpx.Response(
                200,
                text="# Capula Careers\nAll open roles (GET `"
                + BOARD
                + "jobs.md`): 10 current openings",
            )
        if req.url.path.endswith("/jobs.md"):
            suffix = "\nchanged" if changed and reads.count(req.url.path) > 1 else ""
            return httpx.Response(200, text=catalogue() + suffix)
        name = "capula_credit132.md" if "1D78B4440A" in req.url.path else "capula_quant132.md"
        return httpx.Response(200, text=Path("tests/fixtures/" + name).read_text())

    async def run():
        h = HTTPClient(transport=httpx.MockTransport(handler), retries=0)
        try:
            return await build_collector("capula", company(), h).collect()
        finally:
            await h.close()

    if changed:
        with pytest.raises(SourceUnavailable, match="changed during"):
            asyncio.run(run())
    else:
        result = asyncio.run(run())
        assert len(result.jobs) == 1 and result.scope_complete and not result.complete
