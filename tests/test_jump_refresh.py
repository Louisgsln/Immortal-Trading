"""The Jump maintenance script preserves local evidence and never imports offers."""

import hashlib
import importlib.util
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from trading_radar.config import load_config
from trading_radar.http import SourceUnavailable

SCRIPT = Path(__file__).parents[1] / "scripts" / "refresh_jump_lot23.py"
spec = importlib.util.spec_from_file_location("jump_refresh_audit", SCRIPT)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.fixture
def archive(tmp_path, monkeypatch):
    config = load_config()
    monkeypatch.chdir(tmp_path)
    database = tmp_path / "data" / "jobs.db"
    database.parent.mkdir()
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            "CREATE TABLE jobs(id TEXT, score INTEGER);"
            "CREATE TABLE job_sources(external_id TEXT, job_id TEXT, is_active INTEGER, source TEXT);"
        )
        connection.commit()
    config.settings.database_url = "sqlite:///" + str(database)
    monkeypatch.setattr(audit, "load_config", lambda: config)
    root = tmp_path / "data" / "discovery" / "test"
    root.mkdir(parents=True)
    path = root / "catalogue.json"
    payload = {"meta": {"total": 0}, "jobs": []}
    path.write_text(json.dumps(payload), encoding="utf-8")
    manifest = {
        "source": audit.SOURCE,
        "url": audit.API + "jumptrading/jobs?content=true",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "captured_at": "2026-09-17T00:56:12+00:00",
    }
    (root / "capture.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(audit, "BASELINE", path)
    return path, manifest, database


def test_capture_loader_accepts_verified_bytes(archive):
    path, manifest, _ = archive
    payload, result = audit.load_capture(path)
    assert result == manifest
    assert payload == {"meta": {"total": 0}, "jobs": []}


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", "other"),
        ("url", "https://example.com/jobs"),
        ("sha256", "0" * 64),
        ("bytes", 1),
        ("captured_at", "2026-09-17T00:56:12"),
        ("captured_at", "invalid"),
    ],
)
def test_capture_loader_rejects_bad_manifest(archive, field, value):
    path, manifest, _ = archive
    manifest[field] = value
    (path.parent / "capture.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        audit.load_capture(path)


def test_capture_loader_rejects_modified_bytes(archive):
    path, _, _ = archive
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum"):
        audit.load_capture(path)


def test_replay_checks_parser_contract_before_writing_report(archive):
    path, manifest, _ = archive
    path.write_text('{"meta":{"total":1},"jobs":[]}', encoding="utf-8")
    manifest.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
    (path.parent / "capture.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SourceUnavailable, match="incomplete"):
        audit.replay(path, path.parent)
    assert not (path.parent / "analysis.json").exists()


def test_replay_never_initializes_network_and_preserves_database(archive, monkeypatch):
    path, _, database = archive
    before = database.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline replay must never initialize HTTP")

    monkeypatch.setattr(audit, "HTTPClient", forbidden)
    report = audit.replay(path, path.parent)
    assert not report["database_writes"]
    assert not report["absence_can_close"]
    assert report["selected_count"] == 0
    assert database.read_bytes() == before
    collection = json.loads((path.parent / "collection.json").read_text(encoding="utf-8"))
    assert collection == {
        "jobs": [],
        "complete": False,
        "requests": 0,
        "conflicts": [],
        "listing_gaps": [],
    }


@pytest.mark.parametrize(
    "directory", ["sources/unsafe", "config/proofs", "data/discovery", "outside"]
)
def test_output_is_restricted_to_discovery_children(archive, directory):
    with pytest.raises(ValueError, match="dedicated directory"):
        audit.validate_output(Path(directory))


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal", ".lock"])
def test_output_cannot_overwrite_database_or_sidecar_hardlink(archive, suffix):
    path, _, database = archive
    protected = Path(str(database) + suffix)
    if suffix:
        protected.write_bytes(b"protected")
    alias = path.parent / "analysis.json"
    os.link(protected, alias)
    before = protected.read_bytes()
    with pytest.raises(ValueError, match="database"):
        audit.write_json(alias, {"would": "overwrite"})
    assert protected.read_bytes() == before


def test_network_capture_refuses_existing_archive_without_request(archive, monkeypatch):
    import asyncio

    path, _, _ = archive
    calls = []

    class FakeHTTP:
        def __init__(self, **kwargs):
            self.client = type("Client", (), {"event_hooks": {"response": []}})()

        async def get_json(self, *args):
            calls.append(args)

    monkeypatch.setattr(audit, "HTTPClient", FakeHTTP)
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(audit.capture(path.parent))
    assert calls == []
