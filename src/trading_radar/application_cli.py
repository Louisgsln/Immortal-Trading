"""Local application tracking; no notifier, browser, or network client."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import typer
from filelock import Timeout

from trading_radar.applications import ApplicationField, ApplicationStatus
from trading_radar.config import load_config
from trading_radar.storage import Repository

app = typer.Typer(
    help="Track applications locally; never submit an application.", no_args_is_help=True
)


@contextmanager
def repository(config_dir: Path, demo: bool):
    repo = None
    try:
        config = load_config(config_dir)
        repo = Repository("sqlite:///data/demo.db" if demo else config.settings.database_url)
        yield repo
    except KeyError:
        typer.echo("Unknown job ID. Use trading-radar list to find it.", err=True)
        raise typer.Exit(1) from None
    except Timeout:
        typer.echo("Database is busy with another writer; retry after the scan finishes.", err=True)
        raise typer.Exit(1) from None
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None
    except sqlite3.Error:
        typer.echo("Cannot read or update the application database.", err=True)
        raise typer.Exit(1) from None
    finally:
        if repo:
            repo.close()


def display(value):
    typer.echo(json.dumps(value, ensure_ascii=False, indent=2))


@app.command("list")
def list_applications(
    status: ApplicationStatus | None = None,
    due_before: str | None = typer.Option(
        None, help="Actions due on or before YYYY-MM-DD (inclusive)."
    ),
    limit: int = typer.Option(50, min=1, max=1000),
    offset: int = typer.Option(0, min=0),
    config_dir: Path = Path("config"),
    demo: bool = False,
):
    """List tracking records, ordered by action date then score; use --offset for more."""
    with repository(config_dir, demo) as repo:
        display(repo.list_applications(status, due_before, limit, offset))


@app.command("show")
def show(job_id: str, config_dir: Path = Path("config"), demo: bool = False):
    """Show an application record alongside its collected job facts."""
    with repository(config_dir, demo) as repo:
        display(repo.application_details(job_id))


@app.command("history")
def history(job_id: str, config_dir: Path = Path("config"), demo: bool = False):
    """Show local edits, oldest first. No entry is added for an unchanged update."""
    with repository(config_dir, demo) as repo:
        display(repo.application_history(job_id))


@app.command("update")
def update(
    job_id: str,
    status: ApplicationStatus | None = None,
    application_date: str | None = typer.Option(
        None, help="Actual application date: YYYY-MM-DD; never inferred."
    ),
    recruiter: str | None = None,
    notes: str | None = None,
    next_action: str | None = None,
    next_action_date: str | None = typer.Option(None, help="Calendar date: YYYY-MM-DD."),
    clear: list[ApplicationField] | None = typer.Option(
        None, help="Clear a field; repeat for multiple fields."
    ),
    config_dir: Path = Path("config"),
    demo: bool = False,
):
    """Change only supplied fields. Status changes record your decision; they send nothing."""
    changes: dict[str, str | None] = {
        k: v
        for k, v in {
            "status": status,
            "application_date": application_date,
            "recruiter": recruiter,
            "notes": notes,
            "next_action": next_action,
            "next_action_date": next_action_date,
        }.items()
        if v is not None
    }
    for field in clear or []:
        if field.value in changes:
            raise typer.BadParameter(f"Cannot set and clear {field.value} together")
        changes[field.value] = None
    if not changes:
        raise typer.BadParameter("Provide a field to update or --clear FIELD")
    with repository(config_dir, demo) as repo:
        display(repo.update_application(job_id, changes).model_dump(mode="json"))
