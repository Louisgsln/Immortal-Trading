"""Independent reference coverage is exact, snapshot-consistent, bounded and read-only."""

import json

import pytest
from typer.testing import CliRunner

from trading_radar import cli
from trading_radar.config import Company
from trading_radar.coverage import coverage_report, read_reference
from trading_radar.score_audit import ScoreAuditError


def reference(tmp_path, entries):
    path = tmp_path / "reference.json"
    path.write_text(json.dumps(entries))
    return path


def configure(config, repo):
    config.settings.database_url = (
        "sqlite:///" + repo.db.execute("PRAGMA database_list").fetchone()[2]
    )


def test_exact_id_matching_measures_missing_and_unqualified_without_writing(
    config, repo, job, tmp_path
):
    with repo.transaction():
        repo.upsert(job)
    configure(config, repo)
    path = reference(
        tmp_path,
        [
            {"source": "test", "external_id": job.external_id, "title": job.title},
            {"source": "test", "external_id": "missing", "title": job.title},
        ],
    )
    before = repo.db.total_changes
    report = coverage_report(config, path)
    assert report["found"] == report["missing"] == 1
    assert report["reference_coverage_percent"] == 50
    assert report["entries"][1]["found"] is False
    assert report["scope"] == "provided_reference_only"
    assert repo.db.total_changes == before and len(repo.list_jobs()) == 1


def test_secondary_source_association_is_found_without_fuzzy_title_matching(
    config, repo, job, tmp_path
):
    secondary = job.model_copy(deep=True)
    secondary.source = "secondary"
    secondary.external_id = "other-public-id"
    config.companies["secondary"] = Company(name=job.company, ats="fixture", enabled=True)
    with repo.transaction():
        repo.upsert(job)
        merged, _ = repo.upsert(secondary)
    assert merged.id == job.id
    configure(config, repo)
    report = coverage_report(
        config,
        reference(
            tmp_path,
            [
                {
                    "source": "secondary",
                    "external_id": secondary.external_id,
                    "title": secondary.title,
                }
            ],
        ),
    )
    assert report["found"] == 1 and report["entries"][0]["active"]


@pytest.mark.parametrize(
    "entries",
    [
        [],
        [{"source": "test", "external_id": "1"}],
        [{"source": "unknown", "external_id": "1", "title": "Graduate Trader"}],
        [{"source": "test", "external_id": "1", "title": "Graduate Trader"}] * 2,
        [{"source": "test", "external_id": 1, "title": "Graduate Trader"}],
    ],
)
def test_bad_reference_cannot_inflate_coverage(config, tmp_path, entries):
    with pytest.raises(ValueError):
        read_reference(reference(tmp_path, entries), config)


def test_oversized_reference_is_rejected(config, tmp_path):
    path = tmp_path / "large.json"
    path.write_bytes(b" " * 256_001)
    with pytest.raises(ValueError):
        read_reference(path, config)


def test_absent_database_is_not_created(config, tmp_path):
    database = tmp_path / "absent.db"
    config.settings.database_url = f"sqlite:///{database}"
    path = reference(tmp_path, [{"source": "test", "external_id": "1", "title": "Graduate Trader"}])
    with pytest.raises(ScoreAuditError, match="absente"):
        coverage_report(config, path)
    assert not database.exists()


def test_cli_is_offline_and_reports_safe_failure(config, repo, job, tmp_path, monkeypatch):
    with repo.transaction():
        repo.upsert(job)
    configure(config, repo)
    monkeypatch.setattr(cli, "load_config", lambda _: config)
    path = reference(
        tmp_path, [{"source": "test", "external_id": job.external_id, "title": job.title}]
    )
    runner = CliRunner()
    result = runner.invoke(cli.app, ["coverage", "--reference", str(path)])
    assert result.exit_code == 0 and json.loads(result.output)["read_only"]
    path.write_text('{"private-error-text":')
    result = runner.invoke(cli.app, ["coverage", "--reference", str(path)])
    assert result.exit_code == 1 and "private-error-text" not in result.output
