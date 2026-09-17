"""Preview stored-job recalculations without opening a writable repository."""

import sqlite3
from contextlib import closing
from pathlib import Path

from trading_radar.config import Config
from trading_radar.models import Job, utcnow
from trading_radar.scoring import score_job
from trading_radar.storage import SCHEMA, SCHEMA_VERSION

MAX_JOBS = 5_000
MAX_PAYLOAD = 2_000_000
MESSAGES = {
    "missing": "La base locale est absente.",
    "invalid_config": "Une base SQLite locale sur disque est nécessaire.",
    "incompatible": "Le schéma de la base est incompatible.",
    "corrupt": "La base a échoué au contrôle d’intégrité.",
    "invalid_data": "Une offre conservée contient des données incohérentes.",
    "limit_exceeded": "La base dépasse une limite de lecture. Aucun aperçu partiel n’est fourni.",
    "unreadable": "La base locale ne peut pas être lue pour le moment.",
}


class ScoreAuditError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(MESSAGES[code])


def _schema(db: sqlite3.Connection) -> list[tuple]:
    return list(
        db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        )
    )


def _read(config: Config) -> list[Job]:
    url = config.settings.database_url
    if (
        not url.startswith("sqlite:///")
        or url in {"sqlite:///", "sqlite:///:memory:"}
        or "\x00" in url
    ):
        raise ScoreAuditError("invalid_config")
    path = Path(url.removeprefix("sqlite:///")).resolve()
    if not path.is_file():
        raise ScoreAuditError("missing")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        if list(db.execute("PRAGMA quick_check")) != [("ok",)]:
            raise ScoreAuditError("corrupt")
        with closing(sqlite3.connect(":memory:")) as expected:
            expected.executescript(SCHEMA)
            if _schema(db) != _schema(expected):
                raise ScoreAuditError("incompatible")
        if db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] != SCHEMA_VERSION:
            raise ScoreAuditError("incompatible")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ScoreAuditError("corrupt")
        if db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] > MAX_JOBS:
            raise ScoreAuditError("limit_exceeded")
        jobs = []
        for identifier, score, active, size, payload in db.execute(
            "SELECT id,score,is_active,length(payload),substr(payload,1,?) FROM jobs ORDER BY id",
            (MAX_PAYLOAD + 1,),
        ):
            if not isinstance(size, int) or size > MAX_PAYLOAD:
                raise ScoreAuditError("limit_exceeded")
            job = Job.model_validate_json(payload)
            if (
                job.id != identifier
                or job.score_breakdown.total != score
                or active != int(job.is_active)
            ):
                raise ScoreAuditError("invalid_data")
            jobs.append(job)
        return jobs


def _scoring(job: Job) -> dict:
    return {
        "score": job.score_breakdown.total,
        "priority": job.score_breakdown.priority,
        "breakdown": job.score_breakdown.model_dump(mode="json"),
        "desk": job.desk,
        "asset_class": job.asset_class,
    }


def _summary(jobs: list[Job]) -> dict:
    return {
        "total": len(jobs),
        "active": sum(job.is_active for job in jobs),
        "high_priority": sum(job.is_active and job.score_breakdown.total >= 70 for job in jobs),
        "relevant": sum(job.is_active and job.score_breakdown.total >= 55 for job in jobs),
    }


def build_score_audit(config: Config) -> dict:
    """Compare exactly the score/desk/asset fields persisted by update_scoring.

    This is an observation, not an approval token for a later write. No application
    notes, full job descriptions or credentials are included in the report.
    """
    result: dict = {
        "format_version": 1,
        "generated_at": utcnow().isoformat(),
        "read_only": True,
        "status": "ok",
        "error": None,
        "evaluated": 0,
        "changed": 0,
        "score_changed": 0,
        "before": {},
        "after": {},
        "changes": [],
    }
    try:
        jobs = _read(config)
        recalculated = [score_job(job.model_copy(deep=True), config.keywords) for job in jobs]
        changes: list[dict] = [
            {
                "id": old.id,
                "company": old.company,
                "title": old.title,
                "source": old.source,
                "external_id": old.external_id,
                "is_active": old.is_active,
                "before": _scoring(old),
                "after": _scoring(new),
            }
            for old, new in zip(jobs, recalculated, strict=True)
            if _scoring(old) != _scoring(new)
        ]
        result.update(
            evaluated=len(jobs),
            changed=len(changes),
            score_changed=sum(
                change["before"]["score"] != change["after"]["score"] for change in changes
            ),
            before=_summary(jobs),
            after=_summary(recalculated),
            changes=changes,
        )
    except ScoreAuditError as exc:
        result.update(status="error", error={"code": exc.code, "message": str(exc)})
    except sqlite3.Error as exc:
        sqlite_code = (getattr(exc, "sqlite_errorcode", 0) or 0) & 0xFF
        code = (
            "corrupt"
            if sqlite_code in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}
            else "unreadable"
        )
        result.update(status="error", error={"code": code, "message": MESSAGES[code]})
    except OSError:
        result.update(
            status="error", error={"code": "unreadable", "message": MESSAGES["unreadable"]}
        )
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        result.update(
            status="error", error={"code": "invalid_data", "message": MESSAGES["invalid_data"]}
        )
    return result
