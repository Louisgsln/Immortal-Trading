"""Local inspection and resolution, with no transport or notifier initialization."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import typer
from filelock import Timeout

from trading_radar.alerts import AlertDecision, AlertStatus
from trading_radar.application_cli import display
from trading_radar.config import load_config
from trading_radar.storage import Repository

app = typer.Typer(
    help="Inspect and resolve alerts locally. These commands never send messages.",
    no_args_is_help=True,
)


@contextmanager
def repository(config_dir: Path, demo: bool):
    repo = None
    try:
        config = load_config(config_dir)
        repo = Repository("sqlite:///data/demo.db" if demo else config.settings.database_url)
        yield repo
    except KeyError:
        typer.echo("Unknown alert ID. Use trading-radar alerts list --all.", err=True)
        raise typer.Exit(1) from None
    except Timeout:
        typer.echo("Database is busy with another writer; retry after it finishes.", err=True)
        raise typer.Exit(1) from None
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None
    except sqlite3.Error:
        typer.echo("Cannot read or update the alert database.", err=True)
        raise typer.Exit(1) from None
    finally:
        if repo:
            repo.close()


@app.command("list")
def list_alerts(
    status: AlertStatus | None = None,
    all_states: bool = typer.Option(
        False, "--all", help="Include all states; default shows unknown/sending."
    ),
    limit: int = typer.Option(50, min=1, max=1000),
    offset: int = typer.Option(0, min=0),
    config_dir: Path = Path("config"),
    demo: bool = False,
):
    """List alerts with current revision and a summary across all states."""
    with repository(config_dir, demo) as repo:
        display(repo.list_alerts(status, all_states, limit, offset))


@app.command("show")
def show(alert_id: int, config_dir: Path = Path("config"), demo: bool = False):
    """Inspect delivery state and current job/application details."""
    with repository(config_dir, demo) as repo:
        display(repo.alert_details(alert_id))


@app.command("history")
def history(alert_id: int, config_dir: Path = Path("config"), demo: bool = False):
    """Show automatic transitions and operator decisions, oldest first."""
    with repository(config_dir, demo) as repo:
        display(repo.alert_history(alert_id))


@app.command("resolve")
def resolve(
    alert_id: int,
    decision: AlertDecision = typer.Option(
        ...,
        help="received: confirmed receipt; dismiss: abandon; retry: queue again (duplicate risk).",
    ),
    revision: int = typer.Option(..., min=0, help="Current revision from alerts show/list."),
    reason: str = typer.Option(
        ..., help="Your reason/evidence, 1–2000 characters. Never include credentials."
    ),
    config_dir: Path = Path("config"),
    demo: bool = False,
):
    """Record one explicit decision. Retry only queues; a later enabled scan may send."""
    with repository(config_dir, demo) as repo:
        display(repo.resolve_alert(alert_id, decision, revision, reason))
