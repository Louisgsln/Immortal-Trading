"""Health command: offline JSON suitable for a container health probe."""

import json
from pathlib import Path

import typer
import yaml

from trading_radar.config import load_config
from trading_radar.health import check_health


def health(
    config_dir: Path = Path("config"),
    max_age_hours: float = typer.Option(24, min=0.001, max=87600),
):
    """Inspect SQLite and source freshness locally; exit 1 when not ready, 2 for bad config."""
    try:
        report = check_health(load_config(config_dir), max_age_hours=max_age_hours)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        typer.echo(
            json.dumps({"status": "critical", "ready": False, "error": "invalid_configuration"})
        )
        raise typer.Exit(2) from None
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ready"]:
        raise typer.Exit(1)
