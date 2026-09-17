"""Read-only activity trends from the local observation history."""

import json
from pathlib import Path

import typer
import yaml

from trading_radar.config import load_config
from trading_radar.trends import build_trends


def trends(
    config_dir: Path = Path("config"),
    days: int = typer.Option(30, min=1, max=365),
):
    """Summarize recorded activity by UTC day; no collection or notification."""
    try:
        config = load_config(config_dir)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        typer.echo(
            json.dumps(
                {
                    "status": "error",
                    "error": {
                        "code": "invalid_configuration",
                        "message": "Configuration indisponible ou invalide.",
                    },
                },
                ensure_ascii=False,
            )
        )
        raise typer.Exit(1) from None
    report = build_trends(config, days=days)
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "ok":
        raise typer.Exit(1)
