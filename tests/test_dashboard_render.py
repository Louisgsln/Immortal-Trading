import base64
import copy
import hashlib
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from trading_radar import dashboard
from trading_radar.dashboard import export_dashboard, render_dashboard
from trading_radar.notifications import TelegramNotifier


class DashboardDocument(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.tags = []
        self.scripts = []
        self.current_script = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.tags.append((tag, attributes))
        if tag == "script":
            self.current_script = {"attributes": attributes, "text": ""}
            self.scripts.append(self.current_script)

    def handle_endtag(self, tag):
        if tag == "script":
            self.current_script = None

    def handle_data(self, data):
        if self.current_script is not None:
            self.current_script["text"] += data

    def embedded_data(self):
        blocks = [
            script for script in self.scripts if script["attributes"].get("id") == "radar-data"
        ]
        assert len(blocks) == 1
        assert blocks[0]["attributes"].get("type") == "application/json"
        return json.loads(blocks[0]["text"])


@pytest.mark.parametrize(
    "untrusted",
    [
        '</script><img src=x onerror="alert(1)"><script>',
        '</ScRiPt><svg onload="alert(1)">',
        '<!--<script>alert("nested")</script>-->',
        '<a href="javascript:alert(1)">Candidature</a>',
        "Échéance — électricité & dérivés < 3 > 2 \u2028suite\u2029fin",
        '"\\\n\t\r\u0000',
        "__RADAR_CSS__ __RADAR_JS__ __RADAR_DATA__ __RADAR_CSP__",
    ],
)
def test_json_roundtrip_treats_untrusted_fields_as_data(untrusted):
    payload = {"jobs": [{"title": untrusted, "notes": untrusted}], "test": [None, False, 0]}
    before = copy.deepcopy(payload)
    document = DashboardDocument(render_dashboard(payload))
    baseline = DashboardDocument(render_dashboard({}))
    assert document.embedded_data() == payload
    assert payload == before
    # Imported text cannot terminate the JSON script and introduce DOM elements.
    assert document.tags == baseline.tags
    assert len(document.scripts) == len(baseline.scripts)


def test_dashboard_contains_no_external_script_or_stylesheet():
    document = DashboardDocument(render_dashboard({}))
    assert document.embedded_data() == {}
    for tag, attrs in document.tags:
        if tag == "script":
            assert not attrs.get("src")
        if tag == "link":
            assert attrs.get("rel", "").lower() not in {"stylesheet", "preconnect", "dns-prefetch"}
        if tag in {"iframe", "object", "embed"}:
            pytest.fail(f"Unexpected embedded external surface: {tag}")


def test_dashboard_is_a_french_utf8_document():
    html = render_dashboard({"label": "Échéances à vérifier — Genève"})
    assert html.encode("utf-8").decode("utf-8") == html
    document = DashboardDocument(html)
    assert any(tag == "html" and attrs.get("lang") == "fr" for tag, attrs in document.tags)
    assert any(
        tag == "meta" and attrs.get("charset", "").lower() == "utf-8"
        for tag, attrs in document.tags
    )


def test_content_policy_matches_inline_assets_and_disallows_connections():
    html = render_dashboard({})
    document = DashboardDocument(html)
    policies = [
        attrs["content"]
        for tag, attrs in document.tags
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "content-security-policy"
    ]
    assert len(policies) == 1
    policy = policies[0]
    assert "default-src 'none'" in policy
    assert "connect-src 'none'" in policy
    assert "form-action 'none'" in policy
    assert "base-uri 'none'" in policy
    assert "unsafe-inline" not in policy
    styles = re.findall(r"<style>(.*?)</style>", html, flags=re.DOTALL)
    assert len(styles) == 1
    scripts = [
        script["text"]
        for script in document.scripts
        if script["attributes"].get("type") != "application/json"
    ]
    assert len(scripts) == 1
    for source in [*styles, *scripts]:
        digest = base64.b64encode(hashlib.sha256(source.encode("utf-8")).digest()).decode("ascii")
        assert f"'sha256-{digest}'" in policy


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_render_rejects_non_json_numbers(value):
    with pytest.raises(ValueError):
        render_dashboard({"score": value})


@pytest.fixture
def dashboard_config(repo, config, job):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    with repo.transaction():
        repo.upsert(job)
        repo.mark_success("test", 1, 0.1)
    repo.update_application(job.id, {"notes": "Suivi privé — électricité", "recruiter": "Personne"})
    return config


def database_rows(repo):
    return {
        name: [tuple(row) for row in repo.db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for (name,) in repo.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def test_export_preserves_database_and_contains_utf8_private_notes(
    dashboard_config, repo, tmp_path, monkeypatch
):
    def forbid_transport(*args, **kwargs):
        pytest.fail("Export must not initialize a notification transport")

    monkeypatch.setattr(TelegramNotifier, "__init__", forbid_transport)
    before = database_rows(repo)
    destination = tmp_path / "exports" / "échéances.html"
    history = tmp_path / "absent-history"
    report = export_dashboard(dashboard_config, destination, history_dir=history)
    payload = DashboardDocument(destination.read_text(encoding="utf-8")).embedded_data()
    assert report["read_only"] is True
    assert report["jobs"] == 1
    assert report["bytes"] == destination.stat().st_size
    assert payload["jobs"][0]["application"]["notes"] == "Suivi privé — électricité"
    assert database_rows(repo) == before
    assert not history.exists()
    assert not list(destination.parent.glob(".radar-dashboard-*"))
    if os.name != "nt":
        assert destination.stat().st_mode & 0o777 == 0o600


def test_existing_export_requires_explicit_overwrite(dashboard_config, tmp_path):
    destination = tmp_path / "dashboard.html"
    destination.write_bytes(b"previous snapshot")
    with pytest.raises(ValueError):
        export_dashboard(dashboard_config, destination, history_dir=tmp_path / "history")
    assert destination.read_bytes() == b"previous snapshot"
    export_dashboard(
        dashboard_config, destination, history_dir=tmp_path / "history", overwrite=True
    )
    assert (
        DashboardDocument(destination.read_text(encoding="utf-8")).embedded_data()["status"] == "ok"
    )


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal", ".lock"])
def test_export_never_overwrites_database_or_sidecars(dashboard_config, repo, suffix):
    database = Path(repo.db.execute("PRAGMA database_list").fetchone()[2])
    target = Path(str(database) + suffix)
    before = database_rows(repo)
    with pytest.raises(ValueError):
        export_dashboard(dashboard_config, target, overwrite=True)
    assert database_rows(repo) == before


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal", ".lock"])
def test_export_rejects_hardlink_to_database_and_sidecars(dashboard_config, repo, tmp_path, suffix):
    database = Path(repo.db.execute("PRAGMA database_list").fetchone()[2])
    source = Path(str(database) + suffix)
    if not source.exists():
        source.touch()
    target = tmp_path / "alias.html"
    os.link(source, target)
    before = source.read_bytes()
    with pytest.raises(ValueError):
        export_dashboard(dashboard_config, target, overwrite=True)
    assert source.read_bytes() == before
    assert target.samefile(source)


def test_export_rejects_symbolic_link(dashboard_config, tmp_path):
    source = tmp_path / "original.html"
    source.write_bytes(b"keep")
    target = tmp_path / "link.html"
    try:
        target.symlink_to(source)
    except OSError:
        pytest.skip("Symbolic link creation is not permitted on this platform")
    with pytest.raises(ValueError):
        export_dashboard(dashboard_config, target, overwrite=True)
    assert source.read_bytes() == b"keep"


def test_export_never_writes_synced_sources(dashboard_config, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "sources" / "nested" / "reference.html"
    with pytest.raises(ValueError, match="read-only"):
        export_dashboard(dashboard_config, source, overwrite=True)
    assert not source.parent.exists()


@pytest.mark.parametrize("name", ["report", "report.json", "report.db", "report.html.txt"])
def test_export_requires_html_extension(dashboard_config, tmp_path, name):
    destination = tmp_path / name
    with pytest.raises(ValueError):
        export_dashboard(dashboard_config, destination)
    assert not destination.exists()


@pytest.mark.parametrize("existing", [False, True])
def test_missing_database_does_not_publish_or_replace_export(config, tmp_path, existing):
    source = tmp_path / "missing.db"
    config.settings.database_url = f"sqlite:///{source}"
    target = tmp_path / "dashboard.html"
    if existing:
        target.write_bytes(b"previous snapshot")
    with pytest.raises(ValueError):
        export_dashboard(config, target, history_dir=tmp_path / "history", overwrite=True)
    assert not source.exists()
    if existing:
        assert target.read_bytes() == b"previous snapshot"
    else:
        assert not target.exists()


def test_failed_atomic_publication_removes_temporary(dashboard_config, tmp_path, monkeypatch):
    target = tmp_path / "dashboard.html"

    def fail_publication(*args, **kwargs):
        raise OSError("Publication unavailable")

    monkeypatch.setattr(dashboard.os, "link", fail_publication)
    with pytest.raises(OSError):
        export_dashboard(dashboard_config, target, history_dir=tmp_path / "history")
    assert not target.exists()
    assert not list(tmp_path.glob(".radar-dashboard-*"))


def test_rejected_destination_preserves_existing_bytes(dashboard_config, tmp_path):
    directory = tmp_path / "directory.html"
    directory.mkdir()
    existing = directory / "keep.txt"
    existing.write_bytes(b"do not replace")
    before = hashlib.sha256(existing.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        export_dashboard(dashboard_config, directory, overwrite=True)
    assert hashlib.sha256(existing.read_bytes()).hexdigest() == before
