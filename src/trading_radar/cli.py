import asyncio
import importlib.util
import json
import os
import random
import sqlite3
from pathlib import Path

import typer
import yaml
from filelock import FileLock

from trading_radar.alert_cli import app as alerts_app
from trading_radar.application_cli import app as applications_app
from trading_radar.audit import audit_sources
from trading_radar.backup_cli import app as backup_app
from trading_radar.collectors import Collector, FixtureCollector, build_collector
from trading_radar.config import Company, load_config
from trading_radar.dashboard_cli import app as dashboard_app
from trading_radar.deadline_cli import app as deadlines_app
from trading_radar.export import export_csv
from trading_radar.health_cli import health
from trading_radar.http import HTTPClient
from trading_radar.http_cache import JSONCache
from trading_radar.models import utcnow
from trading_radar.monitoring_cli import app as monitor_app
from trading_radar.notifications import TelegramNotifier
from trading_radar.runtime_status import WatcherPulse, pulse_path
from trading_radar.scanner import configure_logging, scan
from trading_radar.score_audit import build_score_audit
from trading_radar.scoring import score_job
from trading_radar.storage import Repository
from trading_radar.trends_cli import trends

app = typer.Typer(
    help="Trading Job Radar — public postings, explainable fit scores.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
app.add_typer(applications_app, name="applications")
app.add_typer(deadlines_app, name="deadlines")
app.add_typer(alerts_app, name="alerts")
app.add_typer(backup_app, name="backup")
app.add_typer(monitor_app, name="monitor")
app.add_typer(dashboard_app, name="dashboard")
app.command()(health)
app.command()(trends)


def runtime_config(directory: Path, demo: bool = False):
    config = load_config(directory)
    if demo:
        config.settings.database_url = "sqlite:///data/demo.db"
        config.settings.alerts_enabled = False
        config.settings.deadline_reminders_enabled = False
        config.companies = {
            "demo": Company(name="DEMO — synthetic jobs", ats="fixture", enabled=True)
        }
    return config


def resources(directory: Path, demo: bool = False, *, notifications: bool = True):
    config = runtime_config(directory, demo)
    repo = Repository(config.settings.database_url)
    notifier = (
        TelegramNotifier.from_env() if notifications and config.settings.alerts_enabled else None
    )
    return config, repo, notifier


@app.command("scan")
def scan_command(
    config_dir: Path = Path("config"),
    company: str | None = None,
    source: str | None = typer.Option(
        None, help="Connector type or configured source key, e.g. workday or goldman_campus."
    ),
    demo: bool = False,
    dry_run: bool = typer.Option(
        False, help="Collect into a temporary snapshot and preview changes without importing."
    ),
):
    """Run once. --demo uses synthetic fixtures and a separate database, without alerts."""
    if dry_run:
        from trading_radar.scan_preview import preview_scan

        try:
            config = runtime_config(config_dir, demo)
        except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
            typer.echo(
                json.dumps(
                    {
                        "format_version": 1,
                        "generated_at": utcnow().isoformat(),
                        "read_only": True,
                        "ephemeral_new_ids": True,
                        "status": "error",
                        "error": {
                            "code": "invalid_configuration",
                            "message": "Configuration unavailable or invalid.",
                        },
                        "metrics": None,
                        "changes": [],
                    }
                )
            )
            raise typer.Exit(1) from None
        collectors: dict[str, Collector] | None = (
            {"demo": FixtureCollector(Path("tests/fixtures/jobs.json"))} if demo else None
        )
        report = asyncio.run(
            preview_scan(config, company=company, source=source, collectors=collectors)
        )
        no_sources = report["status"] == "ok" and not report["metrics"]["sources"]
        if no_sources:
            report["status"] = "error"
            report["error"] = {
                "code": "no_sources",
                "message": "No enabled source matched the filters.",
            }
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
        if no_sources:
            raise typer.Exit(2)
        if report["status"] != "ok":
            raise typer.Exit(1)
        return
    configure_logging()
    config, repo, notifier = resources(config_dir, demo)
    try:
        fixtures: dict[str, Collector] | None = (
            {"demo": FixtureCollector(Path("tests/fixtures/jobs.json"))} if demo else None
        )
        metrics = asyncio.run(
            scan(
                config, repo, company=company, source=source, collectors=fixtures, notifier=notifier
            )
        )
        export_csv(repo, Path("data/demo.csv" if demo else "data/jobs.csv"))
        typer.echo(metrics.model_dump_json(indent=2))
        if metrics.failed:
            raise typer.Exit(1)
        if not metrics.sources:
            typer.echo("No enabled source matched the filters.")
            raise typer.Exit(2)
    finally:
        repo.close()


@app.command()
def watch(config_dir: Path = Path("config")):
    """Continuous monitoring with per-source intervals. Stop with Ctrl+C."""
    configure_logging()
    config, repo, notifier = resources(config_dir)
    if not any(c.enabled for c in config.companies.values()):
        repo.close()
        raise typer.BadParameter("Enable at least one source before watch")
    # Only opted-in collectors use this bounded in-memory cache. Every scan keeps
    # a fresh HTTP client, so robots policies are fetched again between scans.
    json_cache = JSONCache()

    async def loop():
        async with WatcherPulse(config) as pulse:
            while True:
                pulse.check()
                pulse.publish("scanning")
                result = await scan(
                    config, repo, due_only=True, notifier=notifier, json_cache=json_cache
                )
                if result.sources:
                    export_csv(repo, Path("data/jobs.csv"))
                    typer.echo(result.model_dump_json())
                pulse.publish("waiting")
                await asyncio.sleep(10 + random.uniform(0, 3))

    try:
        with FileLock(str(pulse_path(config)) + ".lock", timeout=0):
            asyncio.run(loop())
    except KeyboardInterrupt:
        typer.echo("Watcher stopped.")
    finally:
        repo.close()


@app.command("telegram")
def telegram(config_dir: Path = Path("config")):
    """Private /status commands and incident notices, independent of the watcher."""
    from trading_radar.telegram_control import run_control

    configure_logging()
    config = load_config(config_dir)
    try:
        asyncio.run(run_control(config))
    except KeyboardInterrupt:
        typer.echo("Telegram service stopped.")
    except Exception as error:
        typer.echo(f"Telegram service unavailable ({type(error).__name__}).", err=True)
        raise typer.Exit(1) from None


@app.command("list")
def list_command(
    min_score: int = 0, new: bool = False, demo: bool = False, config_dir: Path = Path("config")
):
    """List stored jobs. --new means first observed on their latest source scan."""
    _, repo, _ = resources(config_dir, demo)
    try:
        for job in repo.list_jobs(min_score, new):
            typer.echo(
                json.dumps(
                    {
                        "id": job.id,
                        "company": job.company,
                        "title": job.title,
                        "location": job.location_normalized,
                        "score": job.score_breakdown.total,
                        "priority": job.score_breakdown.priority,
                        "urgency": job.urgency(),
                        "active": job.is_active,
                        "url": job.apply_url,
                    },
                    ensure_ascii=False,
                )
            )
    finally:
        repo.close()


@app.command()
def stats(demo: bool = False, config_dir: Path = Path("config")):
    _, repo, _ = resources(config_dir, demo)
    try:
        typer.echo(json.dumps(repo.stats(), indent=2))
    finally:
        repo.close()


@app.command("audit")
def audit_command(
    config_dir: Path = Path("config"),
    max_age_hours: float = typer.Option(24, min=0.001, max=87600),
    output: Path | None = None,
):
    """Report source/job freshness offline, without changing observations or creating a database."""
    try:
        config = load_config(config_dir)
        database = Path(config.settings.database_url.removeprefix("sqlite:///")).resolve()
        if output and output.resolve() in {
            database,
            Path(str(database) + "-wal"),
            Path(str(database) + "-shm"),
        }:
            raise ValueError("Audit output cannot overwrite the database")
        report = audit_sources(config, max_age_hours)
    except (ValueError, sqlite3.Error) as exc:
        typer.echo(f"Cannot audit database: {type(exc).__name__}", err=True)
        raise typer.Exit(1) from None
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    typer.echo(text)


@app.command()
def explain(job_id: str, demo: bool = False, config_dir: Path = Path("config")):
    _, repo, _ = resources(config_dir, demo)
    try:
        typer.echo(repo.get(job_id).score_breakdown.model_dump_json(indent=2))
    finally:
        repo.close()


@app.command()
def export(
    output: Path = Path("data/jobs.csv"), demo: bool = False, config_dir: Path = Path("config")
):
    _, repo, _ = resources(config_dir, demo)
    try:
        typer.echo(f"Exported {export_csv(repo, output)} jobs to {output}")
    finally:
        repo.close()


@app.command()
def rescore(demo: bool = False, config_dir: Path = Path("config"), dry_run: bool = False):
    """Recalculate stored jobs with current rules, without network calls or alerts."""
    if dry_run:
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
                    }
                )
            )
            raise typer.Exit(1) from None
        if demo:
            config.settings.database_url = "sqlite:///data/demo.db"
        report = build_score_audit(config)
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
        if report["status"] != "ok":
            raise typer.Exit(1)
        return
    config, repo, _ = resources(config_dir, demo, notifications=False)
    try:
        with FileLock(repo.lock_path, timeout=0), repo.transaction():
            changed = sum(
                repo.update_scoring(score_job(job, config.keywords)) for job in repo.list_jobs()
            )
        export_csv(repo, Path("data/demo.csv" if demo else "data/jobs.csv"))
        typer.echo(json.dumps({"rescored": changed}))
    finally:
        repo.close()


@app.command()
def doctor(network: bool = False, config_dir: Path = Path("config")):
    """Validate config, SQLite and dependencies; --network probes enabled collectors without writes."""
    configure_logging()
    config = load_config(config_dir)
    repo = Repository(config.settings.database_url)
    report: dict = {
        "database": repo.db.execute("PRAGMA quick_check").fetchone()[0],
        "config": "ok",
        "alerts_enabled": config.settings.alerts_enabled,
        "deadline_reminders_enabled": config.settings.deadline_reminders_enabled,
        "telegram_configured": bool(
            os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")
        ),
        "optional_dependencies": {
            name: importlib.util.find_spec(module) is not None
            for name, module in [("JobSpy", "jobspy"), ("ats-scrapers", "ats_scrapers")]
        },
        "sources": {},
    }
    repo.close()

    async def check():
        http = HTTPClient(config.settings.timeout, config.settings.retries)
        try:
            for key, co in config.companies.items():
                if not co.enabled:
                    report["sources"][key] = {"status": "disabled", "notes": co.notes}
                    continue
                try:
                    collector = build_collector(key, co, http)
                    if co.ats in {"jobspy", "ats_dataset"}:
                        module = "jobspy" if co.ats == "jobspy" else "ats_scrapers"
                        if importlib.util.find_spec(module) is None:
                            raise ValueError("optional dependency missing")
                    report["sources"][key] = {"status": "configured"}
                    if network:
                        result = await collector.collect()
                        report["sources"][key] = {"status": "ok", "jobs": len(result.jobs)}
                except Exception as exc:
                    report["sources"][key] = {"status": "failed", "error_type": type(exc).__name__}
        finally:
            await http.close()

    asyncio.run(check())
    typer.echo(json.dumps(report, indent=2))
    if any(s["status"] == "failed" for s in report["sources"].values()) or (
        config.settings.alerts_enabled and not report["telegram_configured"]
    ):
        raise typer.Exit(1)
