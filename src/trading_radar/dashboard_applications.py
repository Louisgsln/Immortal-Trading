"""Local application editing with optimistic concurrency and an atomic audit trail."""

import hashlib
import json
import re
import sqlite3
from contextlib import closing, contextmanager, nullcontext
from datetime import datetime
from pathlib import Path

from filelock import FileLock, Timeout

from trading_radar.applications import Application
from trading_radar.config import Config
from trading_radar.models import utcnow
from trading_radar.storage import SCHEMA, SCHEMA_VERSION

HISTORY_LIMIT = 50
MESSAGES = {
    "invalid_request": "La demande de modification est invalide.",
    "invalid_application": "Vérifiez les champs et les dates de la candidature.",
    "not_found": "Cette candidature est introuvable.",
    "conflict": "Cette candidature a changé. Rechargez-la avant de modifier les champs.",
    "busy": "La base est utilisée par une autre opération. Réessayez dans un instant.",
    "invalid_config": "Une base SQLite locale existante est nécessaire.",
    "protected_database": "Les fichiers de référence ne peuvent pas être modifiés.",
    "incompatible": "Le schéma de la base est incompatible avec cette version.",
    "corrupt": "La base a échoué au contrôle d’intégrité.",
    "invalid_data": "La candidature ou son historique contient des données incohérentes.",
    "unavailable": "La base locale est indisponible pour le moment.",
}


class ApplicationEditError(ValueError):
    """An explicitly safe error suitable for an HTTP response."""

    def __init__(self, code: str, message: str | None = None, status: int = 503):
        self.code = code
        self.message = message or MESSAGES[code]
        self.status = status
        super().__init__(self.message)


def _job_id(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ApplicationEditError("invalid_request", status=400)


def _path(config: Config, writing: bool) -> Path:
    url = config.settings.database_url
    if not url.startswith("sqlite:///") or url in {"sqlite:///", "sqlite:///:memory:"}:
        raise ApplicationEditError("invalid_config", status=400)
    if "\x00" in url:
        raise ApplicationEditError("invalid_config", status=400)
    original = Path(url.removeprefix("sqlite:///"))
    path = original.resolve()
    if writing and any(
        part.casefold() == "sources"
        for candidate in (original.absolute(), path)
        for part in candidate.parts
    ):
        raise ApplicationEditError("protected_database", status=400)
    if not path.is_file():
        raise ApplicationEditError("unavailable")
    return path


def _schema(db: sqlite3.Connection) -> list[tuple]:
    return [
        tuple(row)
        for row in db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        )
    ]


def _validate_database(db: sqlite3.Connection) -> None:
    if [tuple(row) for row in db.execute("PRAGMA quick_check")] != [("ok",)]:
        raise ApplicationEditError("corrupt")
    with closing(sqlite3.connect(":memory:")) as expected:
        expected.executescript(SCHEMA)
        if _schema(db) != _schema(expected):
            raise ApplicationEditError("incompatible")
    if db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] != SCHEMA_VERSION:
        raise ApplicationEditError("incompatible")
    if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ApplicationEditError("corrupt")


@contextmanager
def _connection(config: Config, writing: bool = False):
    try:
        path = _path(config, writing)
        lock = FileLock(str(path) + ".lock", timeout=0) if writing else nullcontext()
        with (
            lock,
            closing(
                sqlite3.connect(
                    path.as_uri() + ("?mode=rw" if writing else "?mode=ro"), uri=True, timeout=0
                )
            ) as db,
        ):
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA foreign_keys=ON")
            if not writing:
                db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN IMMEDIATE" if writing else "BEGIN")
            _validate_database(db)
            yield db
            if writing:
                db.commit()
    except ApplicationEditError:
        raise
    except Timeout:
        raise ApplicationEditError("busy") from None
    except sqlite3.Error as exc:
        code = (getattr(exc, "sqlite_errorcode", 0) or 0) & 0xFF
        safe_code = (
            "busy"
            if code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
            else "corrupt"
            if code in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}
            else "unavailable"
        )
        raise ApplicationEditError(safe_code) from None
    except OSError:
        raise ApplicationEditError("unavailable") from None
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ApplicationEditError("invalid_data") from None


def _snapshot(db: sqlite3.Connection, job_id: str) -> dict:
    row = db.execute("SELECT * FROM applications WHERE job_id=?", (job_id,)).fetchone()
    if row is None:
        raise ApplicationEditError("not_found", status=404)
    application = Application.model_validate(dict(row)).model_dump(mode="json")
    total, last_id = db.execute(
        "SELECT COUNT(*),COALESCE(MAX(id),0) FROM application_history WHERE job_id=?", (job_id,)
    ).fetchone()
    history = []
    for item in db.execute(
        "SELECT * FROM application_history WHERE job_id=? ORDER BY id DESC LIMIT ?",
        (job_id, HISTORY_LIMIT),
    ):
        changed_at = datetime.fromisoformat(item["changed_at"])
        if changed_at.tzinfo is None or changed_at.utcoffset() is None:
            raise ApplicationEditError("invalid_data")
        before = Application.model_validate_json(item["before_payload"]).model_dump(mode="json")
        after = Application.model_validate_json(item["after_payload"]).model_dump(mode="json")
        if before["job_id"] != job_id or after["job_id"] != job_id:
            raise ApplicationEditError("invalid_data")
        history.append(
            {"id": item["id"], "changed_at": item["changed_at"], "before": before, "after": after}
        )
    revision = hashlib.sha256(
        json.dumps([application, last_id], sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return {
        "application": application,
        "revision": revision,
        "history": list(reversed(history)),
        "history_total": total,
        "history_truncated": total > HISTORY_LIMIT,
    }


def read_application(config: Config, job_id: str) -> dict:
    """Read one transactionally consistent record and its most recent 50 changes."""
    _job_id(job_id)
    with _connection(config) as db:
        return _snapshot(db, job_id)


def update_application(config: Config, job_id: str, changes: dict, expected_revision: str) -> dict:
    """Compare the revision under a writer lock, then commit fields and history together."""
    _job_id(job_id)
    allowed = set(Application.model_fields) - {"job_id"}
    if (
        not isinstance(changes, dict)
        or not changes
        or set(changes) - allowed
        or not isinstance(expected_revision, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_revision) is None
    ):
        raise ApplicationEditError("invalid_request", status=400)
    if any(value is not None and not isinstance(value, str) for value in changes.values()):
        raise ApplicationEditError("invalid_application", status=422)
    with _connection(config, writing=True) as db:
        previous = _snapshot(db, job_id)
        if previous["revision"] != expected_revision:
            raise ApplicationEditError("conflict", status=409)
        try:
            updated = Application.model_validate(previous["application"] | changes).model_dump(
                mode="json"
            )
        except (ValueError, TypeError):
            raise ApplicationEditError("invalid_application", status=422) from None
        if updated == previous["application"]:
            return previous
        db.execute(
            "UPDATE applications SET status=?,application_date=?,recruiter=?,notes=?,"
            "next_action=?,next_action_date=? WHERE job_id=?",
            tuple(
                updated[field]
                for field in (
                    "status",
                    "application_date",
                    "recruiter",
                    "notes",
                    "next_action",
                    "next_action_date",
                    "job_id",
                )
            ),
        )
        db.execute(
            "INSERT INTO application_history(job_id,changed_at,before_payload,after_payload) VALUES(?,?,?,?)",
            (
                job_id,
                utcnow().isoformat(),
                json.dumps(previous["application"]),
                json.dumps(updated),
            ),
        )
        return _snapshot(db, job_id)
