"""Local backup commands; no Repository migrations, network or notification transport."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from zipfile import BadZipFile, LargeZipFile

import typer
from filelock import Timeout

from trading_radar.application_cli import display
from trading_radar.backup_retention import plan_retention
from trading_radar.backups import create_backup, database_path, restore_backup, verify_backup
from trading_radar.config import load_config

app = typer.Typer(
    help="Create, verify, restore and audit retention of SQLite backups offline.",
    no_args_is_help=True,
)


@contextmanager
def errors():
    try:
        yield
    except Timeout:
        typer.echo("Destination is locked by another writer; retry after it finishes.", err=True)
        raise typer.Exit(1) from None
    except (ValueError, OSError, sqlite3.Error, BadZipFile) as exc:
        typer.echo(f"Backup operation failed: {exc}", err=True)
        raise typer.Exit(1) from None


def configured_database(config_dir: Path, demo: bool) -> Path:
    config = load_config(config_dir)
    return database_path("sqlite:///data/demo.db" if demo else config.settings.database_url)


@app.command("create")
def create(destination: Path, config_dir: Path = Path("config"), demo: bool = False):
    """Create a new ZIP snapshot of the configured database (including committed WAL)."""
    with errors():
        manifest = create_backup(configured_database(config_dir, demo), destination)
        display({"backup": str(destination), "manifest": manifest})


@app.command("verify")
def verify(archive: Path):
    """Check a backup without configuration, migrations or modification of its contents."""
    with errors():
        display({"backup": str(archive), "manifest": verify_backup(archive)})


@app.command("restore")
def restore(
    archive: Path,
    destination: Path,
    config_dir: Path = Path("config"),
    demo: bool = False,
):
    """Verify and recover into a NEW database. Does not change settings or activate alerts."""
    with errors():
        manifest = restore_backup(
            archive, destination, protected=configured_database(config_dir, demo)
        )
        display({"restored_database": str(destination), "manifest": manifest})


@app.command("plan")
def plan(
    directory: Path,
    keep_latest: int = typer.Option(7, min=1, max=100, help="Always keep the latest N backups."),
    keep_daily: int = typer.Option(
        14, min=0, max=365, help="Keep one backup per UTC day, including today."
    ),
    keep_weekly: int = typer.Option(
        8, min=0, max=104, help="Keep one backup per ISO week, including the current week."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print the complete audit as JSON."),
):
    """Verify local ZIP backups and propose retention. Never delete or move a file."""
    try:
        report = plan_retention(
            directory,
            keep_latest=keep_latest,
            keep_daily=keep_daily,
            keep_weekly=keep_weekly,
        )
    except (ValueError, OSError, sqlite3.Error, BadZipFile, LargeZipFile) as exc:
        typer.echo(f"Backup retention audit failed ({type(exc).__name__}).", err=True)
        raise typer.Exit(1) from None
    if json_output:
        display(report)
    else:
        summary = report["summary"]
        typer.echo(f"Backup retention audit: {report['status']}")
        typer.echo(f"Directory: {json.dumps(report['directory'], ensure_ascii=False)}")
        typer.echo(
            f"Archives: {summary['archives']} | valid: {summary['valid']} | "
            f"invalid: {summary['invalid']} | kept: {summary['kept']} | "
            f"candidates: {summary['candidates']}"
        )
        typer.echo(
            f"Total bytes: {summary['bytes_total']} | candidate bytes: {summary['candidate_bytes']}"
        )
        for entry in report["entries"]:
            name = json.dumps(entry["name"], ensure_ascii=False)
            reasons = ", ".join(entry["reasons"])
            typer.echo(f"{entry['decision']}: {name} ({reasons})")
        typer.echo("Audit only. No file was deleted or moved; no apply command is available.")
    if report["status"] == "blocked":
        raise typer.Exit(1)
