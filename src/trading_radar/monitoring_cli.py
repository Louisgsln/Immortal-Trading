"""Explicit offline health recording and archive inspection."""

import json
from collections.abc import Callable
from pathlib import Path

import typer
import yaml

from trading_radar.config import load_config
from trading_radar.monitoring import history as read_history
from trading_radar.monitoring import read_snapshot, record_health

app = typer.Typer(help="Record and inspect local health snapshots; no scheduling or messages.")


def _run(action: Callable[[], dict]) -> dict:
    try:
        result = action()
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        typer.echo(json.dumps({"error": "monitoring_failed", "error_type": type(exc).__name__}))
        raise typer.Exit(2) from None
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    return result


@app.command()
def record(
    config_dir: Path = Path("config"),
    history_dir: Path = Path("data/health-history"),
    max_age_hours: float = typer.Option(24, min=0.001, max=87600),
):
    """Archive one health report, including critical states (exit 1 after recording)."""
    result = _run(lambda: record_health(load_config(config_dir), history_dir, max_age_hours))
    if not result["report"]["ready"]:
        raise typer.Exit(1)


@app.command()
def history(
    history_dir: Path = Path("data/health-history"),
    status: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = typer.Option(50, min=1, max=200),
    offset: int = typer.Option(0, min=0),
):
    """List verified snapshots, newest first; date bounds are inclusive and timezone-aware."""
    _run(lambda: read_history(history_dir, status, since, until, limit, offset))


@app.command()
def show(identifier: str, history_dir: Path = Path("data/health-history")):
    """Read and verify a complete snapshot by its identifier."""
    _run(lambda: read_snapshot(history_dir, identifier))
