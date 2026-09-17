import asyncio
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import httpx
import pytest

from scripts.measure_workday_cache import main, measure, select_targets
from trading_radar.config import Company


@pytest.fixture
def sample(config, tmp_path):
    config.companies = {
        "demo": Company(
            name="Demo",
            ats="workday",
            enabled=True,
            career_url="https://demo.wd3.myworkdayjobs.com/External",
            request_interval=0.1,
        )
    }
    path = tmp_path / "jobs.db"
    config.settings.database_url = f"sqlite:///{path}"
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE jobs (id TEXT, payload TEXT, is_active INT, score INT)")
        for identifier, active, score in [("low", 1, 20), ("best", 1, 85), ("closed", 0, 99)]:
            db.execute(
                "INSERT INTO jobs VALUES (?,?,?,?)",
                (
                    identifier,
                    json.dumps(
                        {
                            "source": "demo",
                            "apply_url": f"https://demo.wd3.myworkdayjobs.com/External/job/London/{identifier}",
                        }
                    ),
                    active,
                    score,
                ),
            )
        db.commit()
    return config, path


@pytest.fixture(autouse=True)
def no_pacing(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("trading_radar.http.asyncio.sleep", no_sleep)


def test_plan_selects_one_active_job_and_preserves_database(sample):
    config, path = sample
    before = path.read_bytes()
    targets = select_targets(config)
    assert len(targets) == 1
    assert targets[0]["job_id"] == "best"
    assert (
        targets[0]["url"]
        == "https://demo.wd3.myworkdayjobs.com/wday/cxs/demo/External/job/London/best"
    )
    assert path.read_bytes() == before
    assert not Path(str(path) + "-wal").exists()


def test_missing_database_not_created(sample):
    config, path = sample
    path.unlink()
    with pytest.raises(ValueError, match="does not exist"):
        select_targets(config)
    assert not path.exists()


@pytest.mark.parametrize(
    "url", ["https://evil.example/job/x", "https://demo.wd3.myworkdayjobs.com/External/job/../x"]
)
def test_stored_urls_must_match_source_and_safe_path(sample, url):
    config, path = sample
    with closing(sqlite3.connect(path)) as db:
        db.execute("UPDATE jobs SET payload=?", (json.dumps({"source": "demo", "apply_url": url}),))
        db.commit()
    with pytest.raises((ValueError, RuntimeError)):
        select_targets(config)


def test_no_network_without_opt_in(sample, tmp_path, monkeypatch, capsys):
    config, _ = sample
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.measure_workday_cache.load_config", lambda _: config)

    def forbidden(*args, **kwargs):
        pytest.fail("Offline plan attempted network")

    monkeypatch.setattr("scripts.measure_workday_cache.HTTPClient", forbidden)
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "offline-plan"


def test_invalid_output_refused_before_network(sample, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid destination attempted config/network")

    monkeypatch.setattr("scripts.measure_workday_cache.load_config", forbidden)
    with pytest.raises(ValueError, match="data/discovery"):
        main(["--network", "--output", str(tmp_path / "bad.json")])


def test_revalidated_body_observed_without_secrets(sample):
    config, path = sample
    before = path.read_bytes()
    requests = []
    payload = json.loads(Path("tests/fixtures/workday_detail.json").read_text())

    def handler(request):
        requests.append(request)
        assert request.method == "GET"
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.headers.get("if-none-match"):
            assert request.headers["if-none-match"] == '"v1"'
            return httpx.Response(304)
        return httpx.Response(200, json=payload, headers={"etag": '"v1"'})

    report = asyncio.run(
        measure(config, select_targets(config), transport=httpx.MockTransport(handler))
    )
    source = report["sources"][0]
    assert source["status"] == "ok"
    assert source["cache_reused"] is True
    assert source["reads"][1]["same_job_as_first"] is True
    assert [r["status"] for r in source["requests"]] == [404, 200, 304]
    assert source["requests"][1]["decoded_body_bytes"] > 0
    assert source["requests"][2]["decoded_body_bytes"] == 0
    assert report["cache_reused_sources"] == 1
    assert len(requests) == 3
    assert path.read_bytes() == before
    assert "conditional_details" not in config.companies["demo"].options


@pytest.mark.parametrize("restriction", ["robots", "403", "429", "500", "redirect"])
def test_refusal_stops_source_without_retry_or_second_read(sample, restriction):
    config, _ = sample
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return (
                httpx.Response(200, text="User-agent: *\nDisallow: /wday/\n")
                if restriction == "robots"
                else httpx.Response(404)
            )
        return httpx.Response(
            302 if restriction == "redirect" else int(restriction),
            headers={"location": "https://example.com"},
        )

    report = asyncio.run(
        measure(config, select_targets(config), transport=httpx.MockTransport(handler))
    )
    assert report["sources"][0]["status"] == "unavailable"
    assert len(requests) == (1 if restriction == "robots" else 2)
    assert report["cache_reused_sources"] == 0


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"etag": '"v1"', "cache-control": "no-store"},
        {"etag": '"v1"', "set-cookie": "secret=do-not-record"},
    ],
)
def test_uncacheable_responses_do_not_claim_reuse_or_expose_cookie(sample, headers):
    config, _ = sample
    payload = json.loads(Path("tests/fixtures/workday_detail.json").read_text())

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        assert "if-none-match" not in request.headers
        return httpx.Response(200, json=payload, headers=headers)

    report = asyncio.run(
        measure(config, select_targets(config), transport=httpx.MockTransport(handler))
    )
    assert report["sources"][0]["status"] == "ok"
    assert not report["sources"][0]["cache_reused"]
    assert "do-not-record" not in json.dumps(report)


def test_measure_refuses_duplicate_sources_before_client(sample, monkeypatch):
    config, _ = sample
    targets = select_targets(config)

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid plan opened HTTP client")

    monkeypatch.setattr("scripts.measure_workday_cache.HTTPClient", forbidden)
    with pytest.raises(ValueError, match="one job"):
        asyncio.run(measure(config, targets * 2))


def test_sources_without_active_jobs_are_skipped(sample):
    config, path = sample
    with closing(sqlite3.connect(path)) as db:
        db.execute("UPDATE jobs SET is_active=0")
        db.commit()
    targets = select_targets(config)
    assert targets == [{"source": "demo", "status": "skipped", "reason": "no active job"}]

    def forbidden(_):
        pytest.fail("Skipped source made an HTTP request")

    report = asyncio.run(measure(config, targets, transport=httpx.MockTransport(forbidden)))
    assert report["sources"][0]["requests"] == []


def test_more_than_four_sources_refused(sample):
    config, _ = sample
    company = config.companies["demo"]
    config.companies = {f"source{n}": company for n in range(5)}
    with pytest.raises(ValueError, match="four"):
        select_targets(config)


@pytest.mark.parametrize("response", [httpx.Response(304), httpx.Response(200, json={})])
def test_invalid_first_response_stops_before_second_read(sample, response):
    config, _ = sample
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return response

    report = asyncio.run(
        measure(config, select_targets(config), transport=httpx.MockTransport(handler))
    )
    assert report["sources"][0]["status"] == "unavailable"
    assert len(requests) == 2
    assert not report["sources"][0]["cache_reused"]


@pytest.mark.parametrize("target", ["database", "wal", "shm", "journal", "lock"])
def test_output_cannot_overwrite_database_or_sidecar_alias(sample, tmp_path, monkeypatch, target):
    config, database = sample
    monkeypatch.chdir(tmp_path)
    discovery = tmp_path / "data/discovery"
    discovery.mkdir(parents=True)
    suffix = {"database": "", "wal": "-wal", "shm": "-shm", "journal": "-journal", "lock": ".lock"}[
        target
    ]
    protected = Path(str(database) + suffix)
    if suffix:
        protected.write_bytes(b"protected")
    before = protected.read_bytes()
    output = discovery / "alias.json"
    os.link(protected, output)
    monkeypatch.setattr("scripts.measure_workday_cache.load_config", lambda _: config)

    def forbidden(*args, **kwargs):
        pytest.fail("Protected destination opened database or network")

    monkeypatch.setattr("scripts.measure_workday_cache.select_targets", forbidden)
    with pytest.raises(ValueError, match="database or its sidecars"):
        main(["--network", "--output", str(output)])
    assert protected.read_bytes() == before


def test_database_named_json_cannot_be_its_own_output(sample, tmp_path, monkeypatch):
    config, database = sample
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "data/discovery/database.json"
    output.parent.mkdir(parents=True)
    database.rename(output)
    config.settings.database_url = f"sqlite:///{output}"
    before = output.read_bytes()
    monkeypatch.setattr("scripts.measure_workday_cache.load_config", lambda _: config)
    with pytest.raises(ValueError, match="database or its sidecars"):
        main(["--output", str(output)])
    assert output.read_bytes() == before


def test_failed_network_measurement_preserves_report_and_exits_nonzero(
    sample, tmp_path, monkeypatch, capsys
):
    config, _ = sample
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("scripts.measure_workday_cache.load_config", lambda _: config)

    async def failed(*args, **kwargs):
        return {"mode": "network", "sources": [{"source": "demo", "status": "unavailable"}]}

    monkeypatch.setattr("scripts.measure_workday_cache.measure", failed)
    assert main(["--network"]) == 1
    report = json.loads(capsys.readouterr().out)
    saved = json.loads(Path("data/discovery/lot23/workday-cache/report.json").read_text())
    assert report == saved
