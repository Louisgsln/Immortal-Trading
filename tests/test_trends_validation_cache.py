"""Reuse only proven JSON content, never dated counters or database snapshots."""

import json
from collections import OrderedDict
from datetime import UTC, datetime

import pytest

from trading_radar import trends


@pytest.fixture
def cached(monkeypatch):
    monkeypatch.setattr(trends, "_validated_metrics", OrderedDict())
    return trends._validated_metrics


def test_identical_content_is_validated_once_without_retaining_json(cached, monkeypatch):
    original = trends.json.loads
    calls = []

    def observe(raw, **kwargs):
        calls.append(raw)
        return original(raw, **kwargs)

    monkeypatch.setattr(trends.json, "loads", observe)
    raw = '{"failed":{"bank":"HTTP 403"},"successful":12}'
    assert trends._failed_sources(raw) == trends._failed_sources(raw) == 1
    assert calls == [raw]
    assert len(cached) == 1
    assert all(isinstance(key, bytes) and len(key) == 32 for key in cached)
    assert list(cached.values()) == [1]


def test_changed_or_corrupt_old_row_is_read_again(cached, config, repo):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )
    now = datetime(2026, 10, 15, tzinfo=UTC)
    repo.db.execute(
        "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)",
        (now.isoformat(), '{"failed":{}}'),
    )
    repo.db.commit()
    assert trends.build_trends(config, now=now)["summary"]["failed_sources"] == 0
    repo.db.execute("UPDATE scan_runs SET metrics=?", ('{"failed":{"bank":"403"}}',))
    repo.db.commit()
    assert trends.build_trends(config, now=now)["summary"]["failed_sources"] == 1
    repo.db.execute("UPDATE scan_runs SET metrics=?", ('{"failed":{},"failed":{}}',))
    repo.db.commit()
    assert trends.build_trends(config, now=now)["error"]["code"] == "invalid_data"
    repo.db.execute(
        "UPDATE scan_runs SET metrics=?,created_at=?", ('{"failed":{}}', "invalid date")
    )
    repo.db.commit()
    assert trends.build_trends(config, now=now)["error"]["code"] == "invalid_data"


@pytest.mark.parametrize("raw", ['{"failed":{},"duration":NaN}', '{"failed":{}} extra'])
def test_invalid_content_is_never_cached(cached, raw):
    for _ in range(2):
        with pytest.raises((ValueError, json.JSONDecodeError)):
            trends._failed_sources(raw)
    assert not cached


def test_cache_has_a_fixed_memory_bound_and_eviction_revalidates(cached, monkeypatch):
    monkeypatch.setattr(trends, "MAX_VALIDATED_METRICS", 2)
    for index in range(4):
        assert trends._failed_sources(json.dumps({"failed": {}, "new": index})) == 0
    assert len(cached) == 2
    assert trends._failed_sources('{"failed":{"bank":"403"}}') == 1
    assert len(cached) == 2
