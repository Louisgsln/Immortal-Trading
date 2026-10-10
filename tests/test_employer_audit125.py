import html
import json
from pathlib import Path

import pytest

from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.http import SourceUnavailable
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.old_mission_research import research_duties
from trading_radar.scoring import score_job

SAMPLES = json.loads(Path("tests/fixtures/old_mission_research125.json").read_text())


@pytest.mark.parametrize("sample", SAMPLES)
def test_verified_research_is_collected_and_scored_from_duties(sample):
    co = load_config().companies["old_mission"]
    row = dict(
        id=sample["id"],
        internal_job_id=123,
        title=sample["title"],
        company_name=co.name,
        absolute_url=f"https://www.oldmissioncapital.com/careers/?gh_jid={sample['id']}",
        location={"name": "Chicago"},
        metadata=[{"name": "Employment Type", "value": "Full-time"}],
        content=sample["description"],
    )
    (raw,) = parse_board(
        {"jobs": [row], "meta": {"total": 1}}, "old_mission", co, GreenhouseOptions(**co.options)
    )
    scored = score_job(normalize(raw), load_config().keywords)
    assert "QUANT_RESEARCH" in scored.desk
    assert scored.score_breakdown.total >= 70
    assert scored.score_breakdown.junior == 20
    assert scored.score_breakdown.front_office == 15
    assert not scored.score_breakdown.exclusions


@pytest.mark.parametrize("sample", SAMPLES)
@pytest.mark.parametrize(
    "change", ["qualifications", "boilerplate", "duplicate", "missing_duty", "unrelated_title"]
)
def test_research_requires_unique_role_duties_not_firm_text(sample, change):
    title = sample["title"]
    description = html.unescape(sample["description"])
    if change == "qualifications":
        description = description.replace("Responsibilities", "Required Skills")
    elif change == "boilerplate":
        description = "<p>" + description.replace("<ul>", " ").replace("</ul>", " ") + "</p>"
    elif change == "duplicate":
        description += description
    elif change == "missing_duty":
        description = description.replace("trading decisions", "financial reporting").replace(
            "VIX options", "audit reports"
        )
    else:
        title = "Administrative Assistant"
    assert not research_duties(title, description)


@pytest.mark.parametrize(
    "source,company,kind",
    [
        ("other", "Old Mission", "official"),
        ("old_mission", "Another Firm", "official"),
        ("old_mission", "Old Mission", "aggregator"),
    ],
)
def test_research_employer_identity_is_required(source, company, kind):
    sample = SAMPLES[0]
    raw = RawJob(
        company=company,
        title=sample["title"],
        description=sample["description"],
        source=source,
        source_type=kind,
        apply_url="https://example.test/jobs/1",
    )
    assert "QUANT_RESEARCH" not in score_job(normalize(raw), load_config().keywords).desk


@pytest.mark.parametrize(
    "source,field,contract,title",
    [
        (
            "old_mission",
            "Employment Type",
            "Intern",
            "Quantitative Trader - 2027 Micro-Internship Program",
        ),
        ("point72", "Time Type", "Part Time", "Trader Summer Internship 2027"),
    ],
)
def test_observed_contracts_preserved_without_inventing_long_internship(
    source, field, contract, title
):
    co = load_config().companies[source]
    url = (
        "https://www.oldmissioncapital.com/careers/?gh_jid=1"
        if source == "old_mission"
        else "https://boards.greenhouse.io/point72/jobs/1?gh_jid=1"
    )
    # Point72's observed URL route uses the exact board path with its identity query.
    row = dict(
        id=1,
        internal_job_id=2,
        title=title,
        company_name=co.name,
        absolute_url=url,
        location={"name": "Chicago"},
        metadata=[{"name": field, "value": contract}],
        content="<p>Trade options. Internship.</p>",
    )
    if source == "point72":
        row["absolute_url"] = "https://boards.greenhouse.io/point72/jobs/1?gh_jid=1"
    (raw,) = parse_board(
        {"jobs": [row], "meta": {"total": 1}}, source, co, GreenhouseOptions(**co.options)
    )
    assert raw.employment_type == contract
    row["metadata"][0]["value"] = "Unknown Contract"
    with pytest.raises(SourceUnavailable, match="employment type"):
        parse_board(
            {"jobs": [row], "meta": {"total": 1}}, source, co, GreenhouseOptions(**co.options)
        )
