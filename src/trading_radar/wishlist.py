"""Shared bookmarks, independent of applications and the schema-4 radar journal."""

import hashlib
import json
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from tempfile import mkstemp
from uuid import UUID

from trading_radar.config import Config
from trading_radar.dashboard_applications import ApplicationEditError, _path, read_application
from trading_radar.models import utcnow

SCHEMA = """
CREATE TABLE wishlist (job_id TEXT PRIMARY KEY, added_at TEXT NOT NULL) STRICT;
CREATE TABLE wishlist_history (id INTEGER PRIMARY KEY, job_id TEXT NOT NULL,
 changed_at TEXT NOT NULL, action TEXT NOT NULL CHECK(action IN ('add','remove')),
 actor TEXT NOT NULL CHECK(actor IN ('dashboard','telegram'))) STRICT;
PRAGMA user_version=1;
"""


def wishlist_path(database: Path) -> Path:
    return Path(str(database.resolve()) + ".wishlist.sqlite3")


def validate(db: sqlite3.Connection) -> None:
    with closing(sqlite3.connect(":memory:")) as expected:
        expected.executescript(SCHEMA)
        query = "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        if [tuple(r) for r in db.execute(query)] != expected.execute(query).fetchall():
            raise ValueError("Invalid wishlist schema")
    if db.execute("PRAGMA user_version").fetchone()[0] != 1:
        raise ValueError("Invalid wishlist version")
    if [tuple(r) for r in db.execute("PRAGMA quick_check")] != [("ok",)]:
        raise ValueError("Invalid wishlist integrity")
    for row in db.execute(
        "SELECT job_id,added_at FROM wishlist UNION ALL SELECT job_id,changed_at FROM wishlist_history"
    ):
        if str(UUID(row[0])) != row[0] or datetime.fromisoformat(row[1]).utcoffset() is None:
            raise ValueError("Invalid wishlist entry")


@contextmanager
def _connection(path: Path, *, write: bool = False):
    try:
        if path.is_symlink():
            raise ApplicationEditError("unavailable")
        if write and not path.exists():
            descriptor, name = mkstemp(prefix=".wishlist-", dir=path.parent)
            os.close(descriptor)
            staged = Path(name)
            try:
                with closing(sqlite3.connect(staged)) as initial:
                    initial.executescript(SCHEMA)
                    initial.commit()
                try:
                    os.link(staged, path)
                except FileExistsError:
                    pass
            finally:
                staged.unlink(missing_ok=True)
        with closing(
            sqlite3.connect(
                path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=1
            )
        ) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            validate(db)
            yield db
            if write:
                db.commit()
    except ApplicationEditError:
        raise
    except sqlite3.Error as error:
        code = (getattr(error, "sqlite_errorcode", 0) or 0) & 0xFF
        raise ApplicationEditError(
            "busy" if code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED} else "unavailable"
        ) from None
    except (OSError, ValueError, TypeError):
        raise ApplicationEditError("invalid_data") from None


def _snapshot(db: sqlite3.Connection | None, job_id: str) -> dict:
    row = (
        db.execute("SELECT added_at FROM wishlist WHERE job_id=?", (job_id,)).fetchone()
        if db
        else None
    )
    last = (
        db.execute(
            "SELECT COALESCE(MAX(id),0) FROM wishlist_history WHERE job_id=?", (job_id,)
        ).fetchone()[0]
        if db
        else 0
    )
    added = row[0] if row else None
    revision = hashlib.sha256(json.dumps([job_id, added, last]).encode()).hexdigest()
    return {"job_id": job_id, "saved": row is not None, "added_at": added, "revision": revision}


def list_wishlist(config: Config) -> list[dict]:
    path = wishlist_path(_path(config, False))
    if not path.exists():
        return []
    with _connection(path) as db:
        ids = [
            row[0]
            for row in db.execute(
                "SELECT job_id FROM wishlist ORDER BY added_at DESC,job_id LIMIT 5001"
            )
        ]
        if len(ids) > 5000:
            raise ApplicationEditError("invalid_data")
        return [_snapshot(db, job_id) for job_id in ids]


def read_wishlist(config: Config, job_id: str) -> dict:
    read_application(config, job_id)
    path = wishlist_path(_path(config, False))
    if not path.exists():
        return _snapshot(None, job_id)
    with _connection(path) as db:
        return _snapshot(db, job_id)


def set_wishlist(
    config: Config,
    job_id: str,
    saved: bool,
    *,
    actor: str,
    expected_revision: str | None = None,
    now: datetime | None = None,
) -> dict:
    if type(saved) is not bool or actor not in {"dashboard", "telegram"}:
        raise ApplicationEditError("invalid_request", status=400)
    try:
        if str(UUID(job_id)) != job_id:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ApplicationEditError("invalid_request", status=400) from None
    application = read_application(config, job_id)["application"]
    instant = now or utcnow()
    if instant.utcoffset() is None:
        raise ApplicationEditError("invalid_request", status=400)
    path = wishlist_path(_path(config, True))
    with _connection(path, write=True) as db:
        before = _snapshot(db, job_id)
        if expected_revision is not None and expected_revision != before["revision"]:
            raise ApplicationEditError(
                "conflict",
                "La liste de souhaits a changé. Rechargez-la avant de modifier cette offre.",
                409,
            )
        if saved != before["saved"]:
            if saved:
                db.execute("INSERT INTO wishlist VALUES (?,?)", (job_id, instant.isoformat()))
            else:
                db.execute("DELETE FROM wishlist WHERE job_id=?", (job_id,))
            db.execute(
                "INSERT INTO wishlist_history(job_id,changed_at,action,actor) VALUES (?,?,?,?)",
                (job_id, instant.isoformat(), "add" if saved else "remove", actor),
            )
        return {**_snapshot(db, job_id), "application": application}
