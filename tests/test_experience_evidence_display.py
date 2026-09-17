"""Academic coding practice stays visible without becoming a professional minimum."""

import json
from html.parser import HTMLParser

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_data import build_dashboard_data
from trading_radar.experience import experience_requirement
from trading_radar.models import ExperienceEvidence, Job


class EvidenceDocument(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.tags = []
        self.embedded = ""
        self.in_data = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "script" and dict(attrs).get("id") == "radar-data":
            self.in_data = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_data = False

    def handle_data(self, data):
        if self.in_data:
            self.embedded += data


def evidence(kind="industry_or_academia", years=5, excerpt=None):
    return ExperienceEvidence(
        minimum_years=years,
        kind=kind,
        origin="description",
        method="jump_coding_track_record",
        excerpt=excerpt
        or f"{years}+ year track record of solving challenging problems through coding "
        "with real metrics & impact in industry and/or academia.",
    )


def with_evidence(job, item, *, description="", structured=None):
    return job.model_copy(
        update={
            "description_text": description,
            "minimum_experience_years": structured,
            "experience_evidence": [item],
        }
    )


def test_old_job_payload_keeps_exact_two_key_experience_contract(job):
    old = job.model_dump(mode="json")
    old.pop("experience_evidence", None)
    old["description_text"] = "No numeric qualification supplied."
    old["minimum_experience_years"] = None
    loaded = Job.model_validate(old)
    assert loaded.experience_evidence == []
    assert experience_requirement(loaded) == {"minimum_years": None, "category": "unspecified"}


@pytest.mark.parametrize("kind", ["professional", "industry_or_academia", "unspecified"])
def test_evidence_alone_never_supplies_filter_minimum_or_mutates_job(job, kind):
    item = evidence(kind)
    observed = with_evidence(job, item)
    before = observed.model_dump(mode="json")
    assert experience_requirement(observed) == {
        "minimum_years": None,
        "category": "unspecified",
        "evidence": [item.model_dump(mode="json")],
    }
    assert observed.model_dump(mode="json") == before


@pytest.mark.parametrize(
    ("description", "structured", "minimum", "category"),
    [
        ("", 0, 0, "up_to_2"),
        ("", 2, 2, "up_to_2"),
        ("", 7, 7, "over_2"),
        ("3+ years of professional experience", None, 3, "over_2"),
        ("Minimum 3 years experience", 7, 7, "over_2"),
    ],
)
def test_numeric_filter_still_uses_independent_text_and_structured_requirement(
    job, description, structured, minimum, category
):
    result = experience_requirement(
        with_evidence(job, evidence(), description=description, structured=structured)
    )
    assert result["minimum_years"] == minimum
    assert result["category"] == category
    assert result["evidence"][0]["minimum_years"] == 5


def test_exported_evidence_is_detached_from_original_model(job):
    observed = with_evidence(job, evidence())
    before = observed.model_dump(mode="json")
    result = experience_requirement(observed)
    result["evidence"][0]["excerpt"] = "Changed by a consumer"
    result["evidence"].append({"minimum_years": 99})
    assert observed.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "untrusted",
    [
        '</script><img src=x onerror="alert(1)"><script>',
        '</ScRiPt><svg onload="alert(1)">',
        '<a href="javascript:alert(1)">Qualifications</a>',
        "Évidence & pratique < 5 > 2\u2028suite\u2029fin",
        "__RADAR_CSS__ __RADAR_JS__ __RADAR_DATA__ __RADAR_CSP__",
    ],
)
def test_evidence_excerpt_cannot_break_out_of_exported_json_script(job, untrusted):
    observed = with_evidence(job, evidence(excerpt=untrusted))
    payload = {"jobs": [{"experience": experience_requirement(observed)}]}
    document = EvidenceDocument(render_dashboard(payload))
    baseline = EvidenceDocument(render_dashboard({}))
    assert document.tags == baseline.tags
    assert json.loads(document.embedded) == payload
    assert (
        json.loads(document.embedded)["jobs"][0]["experience"]["evidence"][0]["excerpt"]
        == untrusted
    )


@pytest.mark.parametrize(
    ("kind", "years", "structured", "category"),
    [
        ("industry_or_academia", 5, None, "unspecified"),
        ("professional", 2, 2, "up_to_2"),
        ("unspecified", 5, None, "unspecified"),
    ],
)
def test_dashboard_exports_evidence_with_no_database_or_score_changes(
    config, repo, job, tmp_path, kind, years, structured, category
):
    config.settings.database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    item = evidence(kind, years)
    observed = with_evidence(job, item, structured=structured)
    with repo.transaction():
        repo.upsert(observed)
    before = list(repo.db.iterdump())
    result = build_dashboard_data(config, tmp_path / "history")
    assert result["status"] == "ok"
    exported = result["jobs"][0]
    assert exported["experience"] == {
        "minimum_years": structured,
        "category": category,
        "evidence": [item.model_dump(mode="json")],
    }
    assert exported["score"] == observed.score_breakdown.total
    assert exported["score_breakdown"] == observed.score_breakdown.model_dump(mode="json")
    assert list(repo.db.iterdump()) == before
