"""Offline deadline consultation and dry-run reminder planning."""

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import typer

from trading_radar.application_cli import display, repository
from trading_radar.config import load_config
from trading_radar.models import utcnow
from trading_radar.reminders import reminder_plans

app = typer.Typer(
    help="Inspect deadlines and preview reminders without sending anything.", no_args_is_help=True
)


@app.command("list")
def list_deadlines(
    days: int = typer.Option(90, min=1, max=3660),
    min_score: int = typer.Option(0, min=0, max=100),
    include_expired: bool = False,
    config_dir: Path = Path("config"),
    demo: bool = False,
):
    """Show known dates and conflicts; date-only deadlines remain imprecise."""
    now = utcnow()
    config = load_config(config_dir)
    with repository(config_dir, demo) as repo:
        plans = reminder_plans(
            repo,
            config.settings.alert_min_score,
            config.settings.deadline_reminder_max_age_hours,
            now=now,
        )
        selected = [
            p
            for p in plans
            if p["score"] >= min_score
            and (
                p["precision"] == "conflict"
                or p["deadline_date"] is not None
                and (
                    include_expired
                    or (
                        datetime.fromisoformat(p["deadline"]) > now
                        if p["deadline"]
                        else p["deadline_date"] >= now.date().isoformat()
                    )
                )
                and p["deadline_date"] <= (now.date() + timedelta(days=days)).isoformat()
            )
        ]
        selected.sort(key=lambda p: (p["deadline_date"] or "9999", p["job_id"]))
        display(
            {
                "generated_at": now.isoformat(),
                "stored_jobs": len(repo.list_jobs()),
                "known_or_conflicting": len(plans),
                "returned": len(selected),
                "deadlines": selected,
            }
        )


@app.command("reminders")
def preview(config_dir: Path = Path("config"), demo: bool = False):
    """Preview J-7/J-3/J-1 eligibility. No queue writes or notifier initialization."""
    config = load_config(config_dir)
    with repository(config_dir, demo) as repo:
        plans = reminder_plans(
            repo, config.settings.alert_min_score, config.settings.deadline_reminder_max_age_hours
        )
        display(
            {
                "dry_run": True,
                "sending_enabled": False,
                "configured_enabled": not demo
                and config.settings.alerts_enabled
                and config.settings.deadline_reminders_enabled,
                "eligible": sum(p["eligible"] for p in plans),
                "reasons": dict(Counter(p["reason"] or "eligible" for p in plans)),
                "reminders": plans,
            }
        )
