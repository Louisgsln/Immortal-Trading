"""Audited employer identities, real vacancies and strict public links."""

from copy import deepcopy

import pytest

from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.http import SourceUnavailable
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.workday import workday_base

BOARDS = {
    "headlands": (
        "Headlands Technologies LLC",
        "https://job-boards.greenhouse.io/headlandstechnologiesllc/jobs/123",
    ),
    "radix_campus": (
        "Radix Trading University Job Board",
        "https://job-boards.greenhouse.io/radixuniversity/jobs/123",
    ),
    "radix_professionals": (
        "Radix Trading Experienced Job Board",
        "https://job-boards.greenhouse.io/radixexperienced/jobs/123",
    ),
    "3red": ("3Red Partners", "https://job-boards.greenhouse.io/3redpartners/jobs/123"),
    "tudor": ("Tudor Group", "https://job-boards.greenhouse.io/tudorgroup/jobs/123"),
    "acadian": (
        "Acadian Asset Management LLC",
        "https://www.acadian-asset.com/careers/open-positions?gh_jid=123",
    ),
}


def parse(source, **changes):
    cfg = load_config().companies[source]
    row = {
        "id": 123,
        "internal_job_id": 456,
        "title": "Junior Execution Trader",
        "company_name": BOARDS[source][0],
        "absolute_url": BOARDS[source][1],
        "location": {"name": "London"},
        "metadata": None,
        "content": "<p>Trade equities, options and FX. Full-time position.</p>",
        "updated_at": "2026-09-28T09:00:00Z",
    } | changes
    return parse_board(
        {"meta": {"total": 1}, "jobs": [row]}, source, cfg, GreenhouseOptions(**cfg.options)
    )


@pytest.mark.parametrize("source", BOARDS)
def test_official_posting_preserves_identity_and_does_not_invent_publication_or_seniority(source):
    job = parse(source)[0]
    assert job.apply_url == BOARDS[source][1]
    assert job.date_posted is None and job.seniority_hint is None
    assert job.application_deadline is None and job.expected_start_date is None


@pytest.mark.parametrize("source", BOARDS)
@pytest.mark.parametrize(
    "change",
    [
        {"company_name": "Another company"},
        {"id": 124},
        {"absolute_url": "https://evil.example/jobs/123"},
        {"internal_job_id": False},
        {"content": ""},
    ],
)
def test_wrong_employer_identity_or_detail_never_imported(source, change):
    with pytest.raises(SourceUnavailable):
        parse(source, **change)


@pytest.mark.parametrize("source", BOARDS)
@pytest.mark.parametrize(
    "title",
    [
        "General Trading Submissions: Traders, Quants, and Quant Devs",
        "Quantitative Research Intern",
        "Quantitative Business Strategist",
        "ESG Quant Analyst - Stewardship Specialist",
    ],
)
def test_generic_forms_support_and_internships_do_not_become_opportunities(source, title):
    assert not parse(source, title=title)


@pytest.mark.parametrize("source", BOARDS)
@pytest.mark.parametrize(
    "title,excluded", [("Associate Trader", True), ("Analyst / Associate Trader", False)]
)
def test_associate_policy_is_unchanged(source, title, excluded):
    raw = parse(source, title=title)[0]
    assert (
        bool(score_job(normalize(raw), load_config().keywords).score_breakdown.exclusions)
        == excluded
    )


@pytest.mark.parametrize(
    "query", ["gh_jid=124", "gh_jid=123&gh_jid=124", "gh_jid=123&redirect=other", ""]
)
def test_acadian_custom_link_requires_one_matching_identifier(query):
    with pytest.raises(SourceUnavailable, match="URL identity"):
        parse(
            "acadian", absolute_url="https://www.acadian-asset.com/careers/open-positions?" + query
        )


def test_arrowstreet_official_workday_and_bounded_partial_scope():
    cfg = deepcopy(load_config().companies["arrowstreet"])
    assert (
        workday_base(cfg)[1]
        == "https://arrowstreetcapital.wd5.myworkdayjobs.com/wday/cxs/arrowstreetcapital/Arrowstreet"
    )
    assert cfg.scan_interval == 1800 and cfg.options["max_details"] == 80
    cfg.tenant = "another_employer"
    with pytest.raises(ValueError, match="tenant differs"):
        workday_base(cfg)
