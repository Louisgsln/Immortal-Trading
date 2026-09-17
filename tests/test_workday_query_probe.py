import asyncio
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import httpx
import pytest

from scripts import probe_workday_queries as probe
from trading_radar.config import Company


@pytest.fixture
def sample(config, tmp_path):
    config.companies = {
        "citi": Company(
            name="Demo",
            enabled=True,
            ats="workday",
            career_url="https://demo.wd3.myworkdayjobs.com/External",
            request_interval=0.1,
        )
    }
    database = tmp_path / "jobs.db"
    config.settings.database_url = f"sqlite:///{database}"
    site = "https://demo.wd3.myworkdayjobs.com/External"
    with closing(sqlite3.connect(database)) as db:
        db.execute("CREATE TABLE jobs (payload TEXT)")
        db.execute("CREATE TABLE job_sources (source TEXT, apply_url TEXT, last_seen TEXT)")
        for name, stamp in [
            ("known", "2026-09-17T00:00:00+00:00"),
            ("old", "2026-09-16T00:00:00+00:00"),
        ]:
            url = f"{site}/job/London/{name}"
            db.execute("INSERT INTO jobs VALUES (?)", (json.dumps({"apply_url": url}),))
            db.execute("INSERT INTO job_sources VALUES (?,?,?)", ("citi", url, stamp))
        db.commit()
    return config, database


@pytest.fixture(autouse=True)
def no_pacing(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)


def row(name="new", title="Repo Trading Analyst"):
    return {"title": title, "externalPath": f"/job/London/{name}"}


def detail(name="new"):
    return {
        "jobPostingInfo": {
            "id": name,
            "title": "Repo Trading Analyst",
            "jobDescription": "Trade repo, securities finance. Python. Junior graduate role.",
            "location": "London, United Kingdom",
        }
    }


def run(config, handler, terms=None):
    return asyncio.run(
        probe.probe(
            config,
            probe.build_plan(config, "citi", terms or ["repo", "securities finance"]),
            transport=httpx.MockTransport(handler),
        )
    )


def test_baseline_latest_observation_is_not_all_known(sample):
    config, database = sample
    before = database.read_bytes()
    plan = probe.build_plan(config, "citi", ["repo"])
    assert plan["baseline"]["known_paths"] == ["/job/London/known", "/job/London/old"]
    assert plan["baseline"]["latest_observation_at"] == "2026-09-17T00:00:00+00:00"
    assert "latest_observation_paths" not in plan["baseline"]
    assert plan["limits"]["request_interval"] == 2
    assert plan["limits"]["retries"] == 0
    assert config.companies["citi"].options == {}
    assert database.read_bytes() == before


def test_facets_inherit_replace_and_clear_without_mutation(sample):
    config, database = sample
    before = database.read_bytes()
    configured = {"country": ["configured-country"]}
    config.companies["citi"].options["applied_facets"] = configured
    inherited = probe.build_plan(config, "citi", ["repo"])
    assert inherited["applied_facets"] == configured
    replacement = {"jobFamilyGroup": ["public-id-a", "public-id-b"]}
    explicit = probe.build_plan(config, "citi", ["repo"], applied_facets=replacement)
    assert explicit["applied_facets"] == replacement
    assert probe.build_plan(config, "citi", ["repo"], applied_facets={})["applied_facets"] == {}
    explicit["applied_facets"]["jobFamilyGroup"].append("later-change")
    inherited["applied_facets"]["country"].append("later-change")
    assert replacement == {"jobFamilyGroup": ["public-id-a", "public-id-b"]}
    assert configured == {"country": ["configured-country"]}
    assert database.read_bytes() == before


def test_planned_facets_are_sent_and_reported_despite_config_change(sample):
    config, database = sample
    before = database.read_bytes()
    filters = {"country": ["public-a", "public-b"], "jobFamilyGroup": ["public-markets"]}
    plan = probe.build_plan(config, "citi", ["repo", "securities finance"], applied_facets=filters)
    config.companies["citi"].options["applied_facets"] = {"country": ["changed-after-plan"]}
    requests = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        body = json.loads(request.content)
        requests.append(body)
        assert body["appliedFacets"] == filters
        return httpx.Response(200, json={"total": 0, "jobPostings": []})

    report, details = asyncio.run(probe.probe(config, plan, transport=httpx.MockTransport(handler)))
    assert report["status"] == "ok" and details == []
    assert report["applied_facets"] == filters
    assert len(requests) == 2
    assert config.companies["citi"].options["applied_facets"] == {"country": ["changed-after-plan"]}
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "facets",
    [
        ["country"],
        ["=public-id"],
        ["country="],
        ["country=  "],
        ["country=private\nvalue"],
        ["country=private\u200bvalue"],
        ["country=public-id", "country=public-id"],
        ["bad-key=private-value"],
        ["country=" + "x" * 129],
        [f"facet{i}=public-id" for i in range(6)],
        [f"country=public-{i}" for i in range(11)],
    ],
)
def test_invalid_cli_facets_refuse_network_with_sanitized_error(
    sample, tmp_path, monkeypatch, capsys, facets
):
    config, database = sample
    before = database.read_bytes()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(probe, "load_config", lambda _: config)
    monkeypatch.setattr(probe, "HTTPClient", lambda **_: pytest.fail("Unexpected HTTP"))
    output = Path("data/discovery/lot30/rejected")
    args = ["--network", "--output-dir", str(output)]
    for facet in facets:
        args.extend(["--facet", facet])
    assert probe.main(args) == 1
    result = json.loads(capsys.readouterr().out)
    assert result == {
        "status": "error",
        "message": "Invalid configuration, baseline or output; probe stopped",
    }
    assert not output.exists()
    assert database.read_bytes() == before


def test_offline_cli_facets_group_exact_public_ids_under_lot30(sample, tmp_path, monkeypatch):
    config, _ = sample
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(probe, "load_config", lambda _: config)
    monkeypatch.setattr(probe, "HTTPClient", lambda **_: pytest.fail("Unexpected HTTP"))
    output = Path("data/discovery/lot30/filtered-plan")
    assert (
        probe.main(
            [
                "--output-dir",
                str(output),
                "--facet",
                "country=public-a",
                "--facet",
                "country=public-b",
                "--facet",
                "jobFamilyGroup=public-markets",
            ]
        )
        == 0
    )
    plan = json.loads((output / "plan.json").read_text())
    assert plan["applied_facets"] == {
        "country": ["public-a", "public-b"],
        "jobFamilyGroup": ["public-markets"],
    }
    assert config.companies["citi"].options == {}
    assert not (output / "details.json").exists()


def test_legacy_plan_without_facets_inherits_current_config(sample):
    config, _ = sample
    plan = probe.build_plan(config, "citi", ["repo"])
    del plan["applied_facets"]
    config.companies["citi"].options["applied_facets"] = {"country": ["configured-id"]}

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert json.loads(request.content)["appliedFacets"] == {"country": ["configured-id"]}
        return httpx.Response(200, json={"total": 0, "jobPostings": []})

    report, _ = asyncio.run(probe.probe(config, plan, transport=httpx.MockTransport(handler)))
    assert report["applied_facets"] == {"country": ["configured-id"]}


def test_duplicate_detail_ids_fail_closed(sample):
    config, _ = sample

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            return httpx.Response(200, json={"total": 2, "jobPostings": [row("a"), row("b")]})
        return httpx.Response(200, json=detail("same-id"))

    report, details = run(config, handler)
    assert report["status"] == "incomplete"
    assert report["error"]["code"] == "duplicate_detail_id"
    assert len(details) == 1


@pytest.mark.parametrize(
    "second_title,success", [("  REPO Trading Analyst ", True), ("Repo Trading Associate", False)]
)
def test_cross_query_title_consistency(sample, second_title, success):
    config, _ = sample

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            term = json.loads(request.content)["searchText"]
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "jobPostings": [
                        row("a", "Repo Trading Analyst" if term == "repo" else second_title)
                    ],
                },
            )
        return httpx.Response(200, json=detail())

    report, details = run(config, handler)
    assert (report["status"] == "ok") == success
    assert len(details) == int(success)


def test_timeout_stops_source_and_closes_client(sample, monkeypatch):
    config, _ = sample

    async def timeout(*args):
        raise TimeoutError("private value")

    monkeypatch.setattr(probe.WorkdayCollector, "_search", timeout)
    report, details = run(config, lambda _: pytest.fail("Unexpected HTTP"))
    assert report["error"]["code"] == "time_limit"
    assert "private value" not in json.dumps(report)
    assert report["requests"] == 0 and details == []


def test_fixed_limits_override_config_without_mutation(sample, monkeypatch):
    config, _ = sample
    config.companies["citi"].options = {
        "max_results_per_query": 1999,
        "max_details": 999,
        "max_scan_seconds": 1800,
    }

    async def search(self, term):
        assert self.options.max_results_per_query == 200
        assert self.options.max_details == 12
        assert self.options.max_scan_seconds == 180
        assert self.config.request_interval == 2
        assert self.http.retries == 0
        assert self.http.client.timeout.read == 20
        return {}

    monkeypatch.setattr(probe.WorkdayCollector, "_search", search)
    report, _ = run(config, lambda _: pytest.fail("Unexpected HTTP"))
    assert report["status"] == "ok"
    assert config.companies["citi"].options["max_details"] == 999


@pytest.mark.parametrize("value", ["not-a-date", "2026-09-17T00:00:00"])
def test_invalid_baseline_timestamp_rejected(sample, value):
    config, database = sample
    with closing(sqlite3.connect(database)) as db:
        db.execute("UPDATE job_sources SET last_seen=?", (value,))
        db.commit()
    with pytest.raises(ValueError):
        probe.build_plan(config, "citi", ["repo"])


def test_symlink_output_ancestor_refused(sample, tmp_path, monkeypatch):
    config, _ = sample
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data/discovery/lot27"
    root.mkdir(parents=True)
    other = tmp_path / "sources"
    other.mkdir()
    try:
        (root / "alias").symlink_to(other, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this host")
    with pytest.raises(ValueError):
        probe.output_directory(root / "alias/new", config)
    assert list(other.iterdir()) == []


def test_queries_union_only_unseen_details_and_scores(sample):
    config, database = sample
    before = database.read_bytes()
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            rows = [
                row("known"),
                row("old"),
                row("new"),
                row("excluded", "Trading Operations Analyst"),
            ]
            return httpx.Response(200, json={"total": 4, "jobPostings": rows})
        return httpx.Response(200, json=detail(), headers={"set-cookie": "secret=not-recorded"})

    report, details = run(config, handler)
    assert report["status"] == "ok"
    assert report["requests"] == 4
    assert report["unique_selected"] == 3
    assert report["queries"][0]["raw_count"] == 4
    assert report["queries"][0]["selected_count"] == 3
    assert report["queries"][0]["unseen_paths"] == ["/job/London/new"]
    assert len(details) == len(report["details"]) == 1
    assert report["details"][0]["reasons"]
    assert "not-recorded" not in json.dumps([report, details])
    assert not report["database_imported"] and not report["exhaustive"]
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "failure", ["robots", "403", "429", "500", "redirect", "large", "malformed"]
)
def test_failure_stops_all_subsequent_queries_and_details(sample, failure):
    config, database = sample
    requests = []
    before = database.read_bytes()

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return (
                httpx.Response(200, text="User-agent: *\nDisallow: /wday/\n")
                if failure == "robots"
                else httpx.Response(404)
            )
        if failure == "large":
            return httpx.Response(200, json={"total": 201, "jobPostings": []})
        if failure == "malformed":
            return httpx.Response(200, json={"total": 2, "jobPostings": []})
        return httpx.Response(
            302 if failure == "redirect" else int(failure),
            headers={"location": "https://example.com"},
        )

    report, details = run(config, handler)
    assert report["status"] == "incomplete"
    assert len(requests) == (1 if failure == "robots" else 2)
    assert len(report["queries"]) == 1 and details == []
    assert database.read_bytes() == before


def test_detail_bound_stops_before_next_query(sample):
    config, _ = sample
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200, json={"total": 13, "jobPostings": [row(str(i)) for i in range(13)]}
        )

    report, details = run(config, handler)
    assert report["error"]["stage"] == "detail_limit"
    assert details == [] and len(requests) == 2


def test_failed_detail_keeps_only_fully_read_details_no_import(sample):
    config, database = sample
    before = database.read_bytes()

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            return httpx.Response(
                200, json={"total": 3, "jobPostings": [row("a"), row("b"), row("c")]}
            )
        if request.url.path.endswith("/a"):
            return httpx.Response(200, json=detail("a"))
        assert request.url.path.endswith("/b")
        return httpx.Response(200, json={})

    report, details = run(config, handler)
    assert report["status"] == "incomplete"
    assert report["error"]["stage"] == "detail"
    assert len(details) == 1 and details[0]["external_id"] == "a"
    assert database.read_bytes() == before


def test_pagination_fixed_maximum_200(sample):
    config, _ = sample
    offsets = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        body = json.loads(request.content)
        offset = body["offset"]
        offsets.append(offset)
        return httpx.Response(
            200,
            json={
                "total": 200 if offset == 0 else 0,
                "jobPostings": [
                    row(str(i), "Trading Operations Analyst") for i in range(offset, offset + 20)
                ],
            },
        )

    report, details = run(config, handler, ["repo"])
    assert report["status"] == "ok" and details == []
    assert offsets == list(range(0, 200, 20))


@pytest.mark.parametrize(
    "terms", [[], [""], [" "], ["a" * 101], ["a", "b", "c"], ["repo", " REPO "]]
)
def test_invalid_terms_rejected_without_http(sample, terms, monkeypatch):
    config, _ = sample
    monkeypatch.setattr(probe, "HTTPClient", lambda **_: pytest.fail("Unexpected HTTP"))
    with pytest.raises(ValueError):
        probe.build_plan(config, "citi", terms)


@pytest.mark.parametrize("source", ["missing", "disabled", "wrong_ats"])
def test_invalid_source_rejected(sample, source):
    config, _ = sample
    if source == "disabled":
        config.companies["citi"].enabled = False
    elif source == "wrong_ats":
        config.companies["citi"].ats = "greenhouse"
    with pytest.raises(ValueError):
        probe.build_plan(config, "missing" if source == "missing" else "citi", ["repo"])


def test_missing_database_not_created(sample):
    config, database = sample
    database.unlink()
    with pytest.raises(ValueError):
        probe.build_plan(config, "citi", ["repo"])
    assert not database.exists()


def test_offline_immutable_plan_and_hashes(sample, tmp_path, monkeypatch, capsys):
    config, database = sample
    before = database.read_bytes()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(probe, "load_config", lambda _: config)
    monkeypatch.setattr(probe, "HTTPClient", lambda **_: pytest.fail("Offline HTTP"))
    output = Path("data/discovery/lot27/plan")
    assert probe.main(["--output-dir", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "planned"
    assert not (output / "details.json").exists()
    metadata = json.loads((output / "manifest.json").read_text())["artifacts"][0]
    original = (output / "plan.json").read_bytes()
    assert metadata["sha256"] == hashlib.sha256(original).hexdigest()
    assert probe.main(["--output-dir", str(output)]) == 1
    assert (output / "plan.json").read_bytes() == original and database.read_bytes() == before


@pytest.mark.parametrize(
    "destination",
    [
        "sources/probe",
        "data/discovery/lot26/probe",
        "data/discovery/lot27",
        "data/discovery/lot27/../../../sources/probe",
        "data/discovery/lot30",
        "data/discovery/lot30/../../../sources/probe",
        "data/discovery/lot30/../lot29/probe",
    ],
)
def test_invalid_destinations_stop_before_network(sample, tmp_path, monkeypatch, destination):
    config, _ = sample
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(probe, "load_config", lambda _: config)
    monkeypatch.setattr(probe, "HTTPClient", lambda **_: pytest.fail("Unexpected HTTP"))
    assert probe.main(["--network", "--output-dir", destination]) == 1


def test_hardlink_artifact_never_overwritten(sample, tmp_path):
    _, database = sample
    output = tmp_path / "output"
    output.mkdir()
    before = database.read_bytes()
    os.link(database, output / "plan.json")
    with pytest.raises(FileExistsError):
        probe.write_artifact(output, "plan.json", {})
    assert database.read_bytes() == before


def test_network_incomplete_exit_and_artifacts(sample, tmp_path, monkeypatch, capsys):
    config, _ = sample
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(probe, "load_config", lambda _: config)

    async def failed(*args, **kwargs):
        return {"mode": "network", "status": "incomplete"}, []

    monkeypatch.setattr(probe, "probe", failed)
    output = Path("data/discovery/lot27/live")
    assert probe.main(["--network", "--output-dir", str(output)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "incomplete"
    manifest = json.loads((output / "manifest.json").read_text())
    assert len(manifest["artifacts"]) == 3
    for artifact in manifest["artifacts"]:
        assert (
            hashlib.sha256((output / artifact["file"]).read_bytes()).hexdigest()
            == artifact["sha256"]
        )
