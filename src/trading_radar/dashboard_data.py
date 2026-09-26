"""Bounded dashboard observations, without repository migrations or network access."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from trading_radar.applications import Application, ApplicationStatus
from trading_radar.config import Config
from trading_radar.deadlines import resolve_deadline
from trading_radar.education import education_mentions
from trading_radar.experience import experience_requirement
from trading_radar.health import check_health
from trading_radar.missions import mission_excerpts
from trading_radar.models import Job, utcnow
from trading_radar.monitoring import history
from trading_radar.storage import SCHEMA, SCHEMA_VERSION
from trading_radar.trends import build_trends

MAX_JOBS = 5000
MESSAGES = {
    "missing": "La base locale est absente. Effectuez une collecte avant de consulter les offres.",
    "incompatible": "Le schéma de la base est incompatible avec cette version du dashboard.",
    "corrupt": "La base a échoué au contrôle d’intégrité. Vérifiez une sauvegarde.",
    "unreadable": "La base locale ne peut pas être lue pour le moment.",
    "invalid_data": "Une offre ou une candidature contient des données incohérentes.",
    "limit_exceeded": "La base dépasse la limite de 5 000 offres. Aucune liste partielle n’est affichée.",
    "invalid_config": "Le dashboard nécessite une base SQLite locale sur disque.",
}


class DashboardDataError(ValueError):
    """Safe error codes only; SQL contents and filesystem paths stay private."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(MESSAGES[code])


def safe_url(value: str) -> str | None:
    """Only absolute HTTP(S) links without credentials or control characters."""
    if not value or any(character.isspace() or ord(character) < 32 for character in value):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or "\\" in value
            or any(ord(character) == 127 for character in value)
        ):
            return None
        # Accessing port detects malformed numbers and out-of-range ports.
        _ = parsed.port
    except ValueError:
        return None
    return value


def _schema(connection: sqlite3.Connection) -> list[tuple]:
    return [
        tuple(row)
        for row in connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        )
    ]


def _job(row: sqlite3.Row) -> dict:
    job = Job.model_validate_json(row["payload"])
    application = Application.model_validate(
        {
            field: row[field]
            for field in (
                "job_id",
                "status",
                "application_date",
                "recruiter",
                "notes",
                "next_action",
                "next_action_date",
            )
        }
    )
    # An internally inconsistent record must not silently display a plausible value.
    expected = {
        "id": job.id,
        "fingerprint": job.fingerprint,
        "company": job.company_normalized,
        "title": job.title_normalized,
        "location": job.location_normalized,
        "score": job.score_breakdown.total,
        "first_seen": job.first_seen.isoformat(),
        "last_seen": job.last_seen.isoformat(),
        "deadline": job.application_deadline.isoformat() if job.application_deadline else None,
        "is_active": int(job.is_active),
    }
    if any(row[key] != value for key, value in expected.items()) or any(
        instant.tzinfo is None for instant in (job.first_seen, job.last_seen, job.date_updated)
    ):
        raise DashboardDataError("invalid_data")
    deadline = resolve_deadline(job)
    return {
        "id": job.id,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "country": job.country,
        "region": job.region,
        "source": job.source,
        "source_type": job.source_type,
        "score": job.score_breakdown.total,
        "priority": job.score_breakdown.priority,
        "score_breakdown": job.score_breakdown.model_dump(mode="json"),
        "experience": experience_requirement(job),
        "education": education_mentions(job),
        "missions": mission_excerpts(job),
        "is_active": job.is_active,
        "is_expired": job.is_expired,
        "first_seen": job.first_seen.isoformat(),
        "last_seen": job.last_seen.isoformat(),
        "description_text": job.description_text,
        "apply_url": safe_url(job.apply_url),
        "source_url": safe_url(job.source_url),
        "application": application.model_dump(mode="json"),
        "deadline": {
            "precision": deadline.precision,
            "day": deadline.day.isoformat() if deadline.day else None,
            "instant": deadline.instant.isoformat() if deadline.instant else None,
            "source": deadline.source,
            "evidence": deadline.evidence,
        },
    }


def read_jobs(config: Config) -> list[dict]:
    """Read a bounded, validated jobs/applications snapshot without migrations."""
    url = config.settings.database_url
    if (
        not url.startswith("sqlite:///")
        or url in {"sqlite:///", "sqlite:///:memory:"}
        or "\x00" in url
    ):
        raise DashboardDataError("invalid_config")
    try:
        path = Path(url.removeprefix("sqlite:///")).resolve()
        if not path.is_file():
            raise DashboardDataError("missing")
    except ValueError as exc:
        if isinstance(exc, DashboardDataError):
            raise
        raise DashboardDataError("invalid_config") from None
    except OSError:
        raise DashboardDataError("unreadable") from None
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("BEGIN")
            if [tuple(row) for row in db.execute("PRAGMA quick_check")] != [("ok",)]:
                raise DashboardDataError("corrupt")
            with closing(sqlite3.connect(":memory:")) as expected:
                expected.executescript(SCHEMA)
                if _schema(db) != _schema(expected):
                    raise DashboardDataError("incompatible")
            if (
                db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
                != SCHEMA_VERSION
            ):
                raise DashboardDataError("incompatible")
            if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise DashboardDataError("corrupt")
            if db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] > MAX_JOBS:
                raise DashboardDataError("limit_exceeded")
            return [
                _job(row)
                for row in db.execute(
                    "SELECT j.*,a.job_id,a.status,a.application_date,a.recruiter,a.notes,"
                    "a.next_action,a.next_action_date FROM jobs j "
                    "LEFT JOIN applications a ON a.job_id=j.id "
                    "ORDER BY j.score DESC,j.first_seen DESC,j.id"
                )
            ]
    except sqlite3.Error as exc:
        code = getattr(exc, "sqlite_errorcode", 0) or 0
        status = (
            "corrupt"
            if code & 0xFF in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}
            else "unreadable"
        )
        raise DashboardDataError(status) from None
    except DashboardDataError:
        raise
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise DashboardDataError("invalid_data") from None
    except OSError:
        raise DashboardDataError("unreadable") from None


def build_dashboard_data(
    config: Config, history_dir: Path = Path("data/health-history"), now: datetime | None = None
) -> dict:
    """Read one jobs/applications snapshot; health, trends and archives are separate observations.

    Missing, incompatible or corrupt business data produces an explicit error payload.
    Monitoring failures are nonfatal. No archive is created and no setting is changed.
    """
    instant = now or utcnow()
    if instant.tzinfo is None:
        raise ValueError("Dashboard time must include a timezone")
    instant = instant.astimezone(UTC)
    result: dict[str, Any] = {
        "format_version": 1,
        "generated_at": instant.isoformat(),
        "status": "ok",
        "error": None,
        "database": {"status": "ok", "schema_version": SCHEMA_VERSION},
        "jobs": [],
        "summary": {},
        "facets": {},
        "warnings": [],
    }
    try:
        result["jobs"] = read_jobs(config)
    except DashboardDataError as exc:
        result.update(status="error", error={"code": exc.code, "message": str(exc)})
        result["database"] = {"status": exc.code, "schema_version": None}
    try:
        # Health is a separate snapshot, potentially newer than the jobs read.
        # Only propagate a cutoff when the caller explicitly supplied one.
        result["health"] = check_health(config, now=now)
    except (ValueError, OSError, sqlite3.Error):
        result["health"] = {
            "status": "unavailable",
            "ready": False,
            "sources": [],
            "source_summary": {},
            "database": {"status": "unchecked", "schema_version": None},
            "issues": [{"code": "health_unavailable", "severity": "critical", "source": None}],
        }
        result["warnings"].append(
            {"code": "health_unavailable", "message": "Le contrôle de santé est indisponible."}
        )
    try:
        result["monitoring"] = {"status": "ok", **history(history_dir, limit=10)}
    except (ValueError, OSError, sqlite3.Error):
        error = {
            "code": "monitoring_unavailable",
            "message": "L’historique de santé est illisible.",
        }
        result["monitoring"] = {"status": "unavailable", "snapshots": [], "error": error}
        result["warnings"].append(error)
    # Historical counters form a separate read-only observation, like health.
    # Failure of an old scan record must not hide the current jobs snapshot.
    try:
        result["trends"] = build_trends(config, days=90, now=instant)
    except (ValueError, OSError, sqlite3.Error):
        result["trends"] = {
            "status": "error",
            "daily": [],
            "error": {
                "code": "trends_unavailable",
                "message": "Les statistiques historiques sont indisponibles.",
            },
        }
    if result["trends"]["status"] != "ok":
        result["warnings"].append(
            {
                "code": "trends_unavailable",
                "message": "Les statistiques historiques sont indisponibles.",
            }
        )
    jobs = result["jobs"]
    today = instant.date().isoformat()
    result["summary"] = {
        "total": len(jobs),
        "active": sum(job["is_active"] for job in jobs),
        "high_priority": sum(job["is_active"] and job["score"] >= 70 for job in jobs),
        "relevant": sum(job["is_active"] and job["score"] >= 55 for job in jobs),
        "applications_due": sum(
            bool(job["application"]["next_action_date"])
            and job["application"]["next_action_date"] <= today
            for job in jobs
        ),
        "applications_in_progress": sum(
            job["application"]["status"] not in {"New", "Rejected", "Withdrawn", "Closed"}
            for job in jobs
        ),
        "fresh_sources": result["health"]["source_summary"].get("fresh", 0),
        "enabled_sources": sum(company.enabled for company in config.companies.values()),
    }
    result["facets"] = {
        "companies": sorted({job["company"] for job in jobs}),
        "countries": sorted({job["country"] for job in jobs if job["country"]}),
        "sources": sorted({job["source"] for job in jobs}),
        "application_statuses": [status.value for status in ApplicationStatus],
    }
    return result
