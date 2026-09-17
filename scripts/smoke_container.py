"""Exercise the installed CLI and recovery on isolated, synthetic data.

Run inside the image with a fresh volume mounted at /app/data and --network none.
The optional local mode exercises the workflow, without claiming container validation.
Artifacts remain in a unique directory for inspection; no existing database is opened.
"""

import argparse
import csv
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from trading_radar.storage import Repository


def snapshot(database: Path) -> dict[str, list[tuple]]:
    """Read every application table without creating or migrating a database."""
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise RuntimeError("SQLite integrity check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign-key check failed")
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return {
            name: connection.execute(
                'SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid'
            ).fetchall()
            for (name,) in tables
        }
    finally:
        connection.close()


def run_smoke(project_root: Path, data_dir: Path, *, local: bool = False) -> dict:
    if not local and (not hasattr(os, "getuid") or os.getuid() == 0):
        raise RuntimeError("Container smoke requires an unprivileged Unix user")
    # mkdtemp is both a write-permission check and isolation from existing volume data.
    work = Path(tempfile.mkdtemp(prefix="container-smoke-", dir=data_dir))
    (work / "config").mkdir()
    (work / "tests" / "fixtures").mkdir(parents=True)
    (work / "config" / "settings.yaml").write_text(
        "alerts_enabled: false\ndeadline_reminders_enabled: false\nbootstrap_silent: true\n"
        "database_url: sqlite:///data/demo.db\n",
        encoding="utf-8",
    )
    (work / "config" / "companies.yaml").write_text("companies: {}\n", encoding="utf-8")
    shutil.copyfile(project_root / "config/keywords.yaml", work / "config/keywords.yaml")
    shutil.copyfile(project_root / "tests/fixtures/jobs.json", work / "tests/fixtures/jobs.json")
    fixture_count = len(json.loads((work / "tests/fixtures/jobs.json").read_text(encoding="utf-8")))
    environment = {
        key: value
        for key, value in os.environ.items()
        if key != "DATABASE_URL" and not key.startswith("TELEGRAM_")
    }
    environment.update(ALERTS_ENABLED="false", PYTHON_DOTENV_DISABLED="1", PYTHONIOENCODING="utf-8")
    commands: list[list[str]] = []

    def cli(*arguments: str) -> str:
        result = subprocess.run(
            [sys.executable, "-c", "from trading_radar.cli import app; app()", *arguments],
            cwd=work,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        commands.append(list(arguments))
        (work / f"command-{len(commands):02d}.log").write_text(
            result.stdout + result.stderr, encoding="utf-8"
        )
        if result.returncode:
            raise RuntimeError(
                f"CLI failed: {' '.join(arguments)}\n{result.stdout}\n{result.stderr}"
            )
        return result.stdout

    preview = json.loads(cli("scan", "--demo", "--dry-run"))
    if (
        preview["status"] != "ok"
        or preview["metrics"]["new"] != fixture_count
        or not preview["read_only"]
        or (work / "data").exists()
    ):
        raise RuntimeError("Initial preview wrote persistent data or lost synthetic jobs")
    cli("scan", "--demo")
    database = work / "data/demo.db"
    first = snapshot(database)
    cli("scan", "--demo")
    second = snapshot(database)
    if len(first["jobs"]) != fixture_count or len(second["jobs"]) != fixture_count:
        raise RuntimeError("Synthetic job count changed or the repeat scan created duplicates")
    if {row[0] for row in first["jobs"]} != {row[0] for row in second["jobs"]}:
        raise RuntimeError("Repeat scan changed canonical job IDs")
    if len(first["job_sources"]) != len(second["job_sources"]):
        raise RuntimeError("Repeat scan duplicated source associations")
    if first["alerts"] or second["alerts"]:
        raise RuntimeError("The demonstration scan unexpectedly queued alerts")
    with (work / "data/demo.csv").open(encoding="utf-8-sig", newline="") as stream:
        if len(list(csv.DictReader(stream))) != fixture_count:
            raise RuntimeError("CSV export does not contain all synthetic jobs")

    # Populate both histories so restoration checks exercise operator data as well.
    # These are synthetic state transitions only: no notifier is constructed or called.
    repository = Repository(f"sqlite:///{database.as_posix()}")
    try:
        job = repository.list_jobs()[0]
        repository.update_application(job.id, {"status": "Reviewing", "notes": "Recovery drill"})
        with repository.transaction():
            repository.enqueue(job, "container_smoke")
            alert_id = repository.db.execute("SELECT id FROM alerts").fetchone()[0]
            repository.set_alert(alert_id, "sending")
            repository.set_alert(alert_id, "unknown", "Synthetic recovery drill; no delivery")
    finally:
        repository.close()

    before = snapshot(database)
    csv_before = (work / "data/demo.csv").read_bytes()
    repeated_preview = json.loads(cli("scan", "--demo", "--dry-run"))
    if (
        repeated_preview["status"] != "ok"
        or repeated_preview["metrics"]["new"] != 0
        or repeated_preview["changes"]
        or snapshot(database) != before
        or (work / "data/demo.csv").read_bytes() != csv_before
    ):
        raise RuntimeError("Preview changed stored jobs, operator data or the CSV export")
    monitoring = json.loads(cli("monitor", "record"))
    history = json.loads(cli("monitor", "history"))
    shown = json.loads(cli("monitor", "show", monitoring["id"]))
    if (
        shown != monitoring
        or history["total"] != 1
        or monitoring["report"]["alerts"]["unknown"] != 1
        or monitoring["report"]["status"] != "degraded"
    ):
        raise RuntimeError("Monitoring did not preserve the synthetic health observation")
    dashboard = json.loads(cli("dashboard", "export", "dashboard.html"))
    if dashboard["jobs"] != fixture_count or not (work / "dashboard.html").is_file():
        raise RuntimeError("Dashboard export did not include the synthetic jobs")
    trends = json.loads(cli("trends", "--days", "7"))
    if (
        trends["status"] != "ok"
        or trends["summary"]["new_jobs"] != fixture_count
        or trends["summary"]["scans"] != 2
    ):
        raise RuntimeError("Historical counters did not match the synthetic workflow")
    cli("backup", "create", "snapshot.zip", "--demo")
    cli("backup", "verify", "snapshot.zip")
    retention = json.loads(cli("backup", "plan", ".", "--json"))
    if (
        retention["status"] != "ok"
        or retention["summary"]["valid"] != 1
        or retention["summary"]["kept"] != 1
        or retention["summary"]["candidates"] != 0
        or retention["deletion_performed"] is not False
    ):
        raise RuntimeError("Retention audit did not preserve the verified synthetic backup")
    cli("backup", "restore", "snapshot.zip", "data/restored.db", "--demo")
    restored = work / "data/restored.db"
    if snapshot(restored) != before or snapshot(database) != before:
        raise RuntimeError("Backup/restore changed table contents")
    # Opening the restored copy via the real application must preserve every row too.
    repository = Repository(f"sqlite:///{restored.as_posix()}")
    try:
        if len(repository.list_jobs()) != fixture_count:
            raise RuntimeError("Restored database is not readable by the application")
        if repository.get_alert(alert_id)["status"] != "unknown":
            raise RuntimeError("Restoration changed an uncertain alert")
    finally:
        repository.close()
    if snapshot(restored) != before:
        raise RuntimeError("Opening the restored copy changed table contents")
    report = {
        "status": "ok",
        "mode": "local_workflow_only" if local else "container",
        "uid": os.getuid() if hasattr(os, "getuid") else None,
        "directory": str(work),
        "synthetic_jobs": fixture_count,
        "preview_new_jobs": preview["metrics"]["new"],
        "table_counts": {name: len(rows) for name, rows in before.items()},
        "identical_tables": len(before),
        "health_snapshots": history["total"],
        "dashboard_jobs": dashboard["jobs"],
        "trends_scans": trends["summary"]["scans"],
        "retention_verified": retention["summary"]["valid"],
        "commands": commands,
    }
    (work / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("/app/data"))
    parser.add_argument(
        "--local", action="store_true", help="Exercise locally without checking the container UID"
    )
    arguments = parser.parse_args()
    report = run_smoke(
        Path(__file__).resolve().parents[1], arguments.data_dir, local=arguments.local
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
