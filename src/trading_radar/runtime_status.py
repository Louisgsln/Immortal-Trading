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
from trading_radar.display_time import format_paris
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
            "pid": os.getpid(),
            "phase": "starting",
            "scan_started": None,
        }

    def publish(self, phase: str | None = None, *, scan_started: datetime | None = None) -> None:
        now = utcnow().isoformat()
        if phase:
            self.value["phase"] = phase
            self.value["scan_started"] = (
                (scan_started.isoformat() if scan_started else now) if phase == "scanning" else None
            )
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
    observed = {source["source"]: source["status"] for source in health["sources"]}
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
        "source_counts": {
            "enabled": sum(company.enabled for company in config.companies.values()),
            "employers": len(
                {company.name for company in config.companies.values() if company.enabled}
            ),
            "fresh": (
                health["source_summary"].get("fresh", 0)
                if health["database"]["status"] == "ok"
                else None
            ),
        },
        "source_inventory": [
            {"source": key, "company": company.name, "status": observed.get(key, "unknown")}
            for key, company in config.companies.items()
            if company.enabled
        ],
    }


def incident_keys(report: dict) -> list[str]:
    keys = [i["code"] + ":" + str(i.get("source", "")) for i in report["health"]["issues"]]
    if report["watcher"]["status"] != "active":
        keys.append("watcher:" + report["watcher"]["status"])
    return sorted(set(keys))


SOURCE_LABELS = {
    "fresh": "à jour",
    "recent_failure": "collecte en échec",
    "stale": "collecte ancienne",
    "never_scanned": "jamais collectée",
    "partial": "fiches incomplètes",
    "collection_degraded": "références contradictoires",
    "access_restricted": "accès bloqué · CAPTCHA",
    "invalid_timestamp": "date incohérente",
}
WATCHER_LABELS = {
    "active": "actif",
    "stopped": "arrêté",
    "stale": "sans signal récent",
    "unknown": "activité non vérifiable",
    "long_scan": "cycle supérieur à 30 minutes",
}


def _short(value: str, limit: int) -> str:
    text = " ".join(value.split())
    encoded = text.encode("utf-16-le")
    return (
        text
        if len(encoded) <= limit * 2
        else encoded[: (limit - 1) * 2].decode("utf-16-le", errors="ignore") + "…"
    )


def _summary(report: dict) -> str:
    health = report["health"]
    sources = (
        f"{health['source_summary'].get('fresh', 0)}/{len(health['sources'])} sources à jour"
        if health["database"]["status"] == "ok"
        else "État des sources indisponible"
    )
    return sources + (
        " · alertes actives" if report["alerts_enabled"] else " · alertes désactivées"
    )


def _problems(report: dict, limit: int, *, details: str = "/status") -> list[str]:
    health = report["health"]
    lines = []
    if health["database"]["status"] != "ok":
        lines.append("Base locale inaccessible ou à vérifier.")
    if report["watcher"]["status"] != "active":
        lines.append("Collecteur " + WATCHER_LABELS[report["watcher"]["status"]] + ".")
    codes = {issue["code"] for issue in health["issues"] if not issue.get("source")}
    if "alerts_need_review" in codes:
        lines.append("Livraison d’alertes à vérifier · /status")
    if "no_enabled_sources" in codes:
        lines.append("Aucune source surveillée.")
    if "scan_invalid_timestamp" in codes:
        lines.append("Date du dernier cycle incohérente.")
    known = {"alerts_need_review", "no_enabled_sources", "scan_invalid_timestamp"}
    if any(code not in known and not code.startswith("database_") for code in codes):
        lines.append("Un contrôle du radar demande une vérification · /status")
    affected = {issue.get("source") for issue in health["issues"] if issue.get("source")}
    problems = [s for s in health["sources"] if s["status"] != "fresh" or s["source"] in affected]
    for source in problems[:limit]:
        label = SOURCE_LABELS.get(source["status"], "à vérifier")
        if source["status"] == "fresh":
            label = (
                "références contradictoires" if source.get("collection_conflicts") else "à vérifier"
            )
        # The failure label is a curated explanation, never the raw employer error.
        elif source.get("failure") and source["status"] == "recent_failure":
            label = _short(source["failure"]["label"], 110)
        channel = (
            " · Campus"
            if source["source"].endswith("_campus")
            else " · Professionnels"
            if source["source"].endswith("_professionals")
            else ""
        )
        lines.append(_short(source["company"], 65) + channel + " · " + label)
        schedule = source.get("schedule", {})
        if source.get("failure") and schedule.get("eligible_now") is False:
            retry = format_paris(schedule.get("next_eligible_at"), unknown="")
            if retry:
                lines.append("Reprise possible dès " + retry)
    if len(problems) > limit:
        lines.append(f"+ {len(problems) - limit} autres sources · {details}")
    return lines


def format_incident_notice(report: dict) -> str:
    """Automatic notices summarize the current state, without the full /status."""
    problems = _problems(report, 3)
    heading = (
        "⚠️ Radar à surveiller" if incident_keys(report) or problems else "✅ Radar opérationnel"
    )
    lines = [heading, "", *problems]
    if problems:
        lines.append("")
    lines += [_summary(report), format_paris(report["health"].get("generated_at"), unknown="")]
    if problems:
        lines.append("Détails · /status")
    return "\n".join(lines).rstrip()


def format_status(report: dict) -> str:
    health, watcher = report["health"], report["watcher"]
    counts = report.get("source_counts")
    lines = [
        "📡 Radar · " + WATCHER_LABELS[watcher["status"]],
        *(
            [
                f"Couverture · {counts['enabled']} sources · {counts['employers']} employeurs"
            ]
            if counts is not None
            else []
        ),
        _summary(report),
        f"Seuil des alertes · {report['threshold']}/100",
        "",
        "Dernier cycle · " + format_paris(health["latest_scan"]),
        "Dernier signal · " + format_paris(watcher["at"]),
    ]
    problems = _problems(report, 8, details="dashboard")
    if problems:
        lines += ["", *problems]
    if report["deliveries"] is not None:
        deliveries = report["deliveries"]
        lines += [
            "",
            f"{deliveries.get('sent', 0)} alertes envoyées · {deliveries.get('pending', 0)} en attente",
        ]
        uncertain = deliveries.get("unknown", 0) + deliveries.get("sending", 0)
        if uncertain:
            lines.append(f"{uncertain} livraisons à vérifier")
    else:
        lines += ["", "Compteur des alertes indisponible"]
    return "\n".join(lines)


def format_sources(report: dict, page: int = 1) -> str:
    """Same configured inventory as /status, in bounded private Telegram pages."""
    sources = sorted(
        report.get("source_inventory", report["health"]["sources"]),
        key=lambda row: (row["company"].casefold(), row["source"]),
    )
    pages = max(1, (len(sources) + 29) // 30)
    if not 1 <= page <= pages:
        return f"Page indisponible. Utilise /sources 1 à /sources {pages}."
    lines = [f"📚 {len(sources)} sources surveillées · page {page}/{pages}", ""]
    for row in sources[(page - 1) * 30 : page * 30]:
        label = SOURCE_LABELS.get(row["status"], "état indisponible")
        lines.append(
            "• "
            + _short(row["company"], 40)
            + " · "
            + _short(row["source"], 30)
            + " · "
            + _short(label, 35)
        )
    if page < pages:
        lines += ["", f"Suite · /sources {page + 1}"]
    return "\n".join(lines)
