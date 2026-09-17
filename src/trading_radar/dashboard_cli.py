"""Local dashboard modes; no collection or notification transport."""

import json
from contextlib import contextmanager
from pathlib import Path

import typer
import yaml

from trading_radar.config import load_config
from trading_radar.dashboard import create_dashboard_server, export_dashboard, render_dashboard
from trading_radar.dashboard_data import build_dashboard_data

app = typer.Typer(
    help="Export a read-only snapshot or serve a local dashboard with optional application editing.",
    no_args_is_help=True,
)


@contextmanager
def errors():
    try:
        yield
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        typer.echo(
            "Dashboard unavailable: check configuration, database and destination.", err=True
        )
        raise typer.Exit(1) from None


@app.command("export")
def export(
    destination: Path,
    config_dir: Path = Path("config"),
    history_dir: Path = Path("data/health-history"),
    overwrite: bool = False,
):
    """Write one self-contained HTML snapshot. --overwrite explicitly replaces the target."""
    with errors():
        typer.echo(
            json.dumps(
                export_dashboard(
                    load_config(config_dir), destination, history_dir, overwrite=overwrite
                ),
                ensure_ascii=False,
                indent=2,
            )
        )


@app.command()
def serve(
    config_dir: Path = Path("config"),
    history_dir: Path = Path("data/health-history"),
    port: int = typer.Option(8765, min=1024, max=65535),
    edit_applications: bool = typer.Option(
        False, help="Enable local application editing with history and conflict checks."
    ),
):
    """Serve on 127.0.0.1; read-only unless --edit-applications is supplied. Stop with Ctrl+C."""
    with errors():
        config = load_config(config_dir)
        if edit_applications:
            from trading_radar.dashboard_editor import create_editable_dashboard_server

            server = create_editable_dashboard_server(config, history_dir, port)
        else:
            data = build_dashboard_data(config, history_dir=history_dir)
            server = create_dashboard_server(render_dashboard(data), port)
        mode = "Application editor" if edit_applications else "Dashboard snapshot"
        typer.echo(f"{mode}: http://127.0.0.1:{port} — Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            typer.echo("Dashboard stopped.")
        finally:
            server.server_close()
