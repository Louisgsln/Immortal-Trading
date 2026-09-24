"""Read-only live status; the watcher pulse is separate from business SQLite."""

import asyncio
import json
import os
import sqlite3
from contextlib import closing, suppress
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from trading_radar.audit import timestamp
from trading_radar.backups import database_path
from trading_radar.config import Config
from trading_radar.health import check_health
from trading_radar.models import utcnow


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def pulse_path(config: Config) -> Path:
    return database_path(config.settings.database_url).with_suffix(".watch.json")


class WatcherPulse:
    def __init__(self, config: Config):
        self.path = pulse_path(config)
        self.value = {
            "version": 1,
            "instance": uuid4().hex,
            "phase": "starting",
            "scan_started": None,
        }

    def publish(self, phase: str | None = None) -> None:
        now = utcnow().isoformat()
        if phase:
            self.value["phase"] = phase
            self.value["scan_started"] = now if phase == "scanning" else None
        self.value["at"] = now
        atomic_json(self.path, self.value)

    async def ticking(self) -> None:
        while True:
            try:
                await asyncio.wait_for(asyncio.Event().wait(), timeout=10)
            except TimeoutError:
                pass
            self.publish()

    async def __aenter__(self):
        self.publish()
        self.task = asyncio.create_task(self.ticking())
        return self

    async def __aexit__(self, *args):
        self.task.cancel()
        with suppress(asyncio.CancelledError):
            await self.task
        self.publish("stopped")

    def check(self) -> None:
        if self.task.done():
            self.task.result()


def watcher_status(config: Config, now: datetime | None = None) -> dict:
    now = now or utcnow()
    try:
        value = json.loads(pulse_path(config).read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("version") != 1:
            raise ValueError("Invalid pulse")
        at = timestamp(value.get("at"))
        phase = value.get("phase")
        if at is None or phase not in {"starting", "scanning", "waiting", "stopped"}:
            raise ValueError("Invalid pulse")
        age = (now - at).total_seconds()
        if age < 0:
            raise ValueError("Future pulse")
        status = "stopped" if phase == "stopped" else "stale" if age > 90 else "active"
        if status == "active" and phase == "scanning":
            started = timestamp(value.get("scan_started"))
            if started is None or started > now:
                raise ValueError("Invalid scan start")
            if (now - started).total_seconds() > 1800:
                status = "long_scan"
        return {"status": status, "phase": phase, "at": at.isoformat(), "age_seconds": round(age)}
    except (OSError, ValueError, TypeError):
        return {"status": "unknown", "phase": None, "at": None, "age_seconds": None}


def runtime_report(config: Config) -> dict:
    health = check_health(config)
    counts = None
    try:
        with closing(
            sqlite3.connect(
                database_path(config.settings.database_url).as_uri() + "?mode=ro",
                uri=True,
                timeout=1,
            )
        ) as db:
            db.execute("PRAGMA query_only=ON")
            counts = dict(db.execute("SELECT status,COUNT(*) FROM alerts GROUP BY status"))
    except sqlite3.Error:
        pass
    return {
        "health": health,
        "watcher": watcher_status(config),
        "deliveries": counts,
        "alerts_enabled": config.settings.alerts_enabled,
        "threshold": config.settings.alert_min_score,
    }


def incident_keys(report: dict) -> list[str]:
    keys = [i["code"] + ":" + str(i.get("source", "")) for i in report["health"]["issues"]]
    if report["watcher"]["status"] != "active":
        keys.append("watcher:" + report["watcher"]["status"])
    return sorted(set(keys))


def format_status(report: dict) -> str:
    health, watcher = report["health"], report["watcher"]

    def moment(value):
        parsed = timestamp(value)
        return parsed.strftime("%d/%m/%Y %H:%M:%S UTC") if parsed else "inconnu"

    labels = {
        "active": "activité récente confirmée",
        "stopped": "arrêté",
        "stale": "plus de signal récent",
        "unknown": "activité non vérifiable",
        "long_scan": "cycle supérieur à 30 minutes, à vérifier",
    }
    source_labels = {
        "fresh": "à jour",
        "recent_failure": "dernier essai en échec",
        "stale": "ancienne collecte",
        "never_scanned": "jamais collectée",
        "invalid_timestamp": "date incohérente",
    }
    lines = [
        "📡 ÉTAT DU RADAR",
        "",
        "Collecteur : " + labels[watcher["status"]],
        "Dernier signal : " + moment(watcher["at"]),
        "Dernier cycle terminé : " + moment(health["latest_scan"]),
        "Base : " + ("accessible" if health["database"]["status"] == "ok" else "à vérifier"),
        f"Alertes offres : {'activées' if report['alerts_enabled'] else 'désactivées'} — seuil {report['threshold']}/100",
        "",
        (
            f"Sources : {len(health['sources'])} surveillées"
            if health["database"]["status"] == "ok"
            else "Sources : état indisponible"
        ),
    ]
    for status, count in sorted(health["source_summary"].items()):
        lines.append(f"• {count} {source_labels.get(status, status)}")
    problems = [s for s in health["sources"] if s["status"] != "fresh"]
    if problems:
        lines += ["", "Sources à vérifier :"] + [
            f"• {s['company']} ({s['source']}) : {source_labels.get(s['status'], s['status'])}"
            for s in problems[:12]
        ]
        if len(problems) > 12:
            lines.append(f"… et {len(problems) - 12} autres.")
    if report["deliveries"] is not None:
        deliveries = report["deliveries"]
        lines += [
            "",
            f"Alertes offres envoyées : {deliveries.get('sent', 0)}",
            f"En attente : {deliveries.get('pending', 0)} ; livraison à vérifier : {deliveries.get('unknown', 0) + deliveries.get('sending', 0)}",
        ]
    lines += [
        "",
        "Contrôle local : si ce PC est éteint ou hors ligne, le bot ne peut pas répondre.",
    ]
    return "\n".join(lines)
