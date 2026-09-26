"""SQLite repository. All persistence lives here to allow a PostgreSQL replacement.

One scanner process owns collection; short writer locks protect state changes.
Source identities remain separate from canonical job identity.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from filelock import FileLock

from trading_radar.alerts import SYSTEM_TRANSITIONS, AlertDecision, AlertStatus, resolved_status
from trading_radar.applications import Application, ApplicationStatus, calendar_date
from trading_radar.models import Job, utcnow
from trading_radar.normalizer import canonical_url, digest

SOURCE_RANK = {"official": 0, "ats": 1, "board": 2, "aggregator": 3, "fixture": 4}
SCHEMA_VERSION = 4
CONTENT_FIELDS = (
    "title",
    "description_text",
    "location_normalized",
    "application_deadline",
    "expected_start_date",
    "minimum_experience_years",
    "experience_evidence",
    "seniority_hint",
    "role_hint",
    "employment_type",
    "apply_url",
)


def source_identity(job: Job) -> str:
    return digest(job.company_normalized, job.external_id or canonical_url(job.apply_url))


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES(1);
CREATE TABLE IF NOT EXISTS jobs(
 id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, company TEXT NOT NULL,
 title TEXT NOT NULL, location TEXT NOT NULL, score INTEGER NOT NULL,
 first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, deadline TEXT,
 is_active INTEGER NOT NULL, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS jobs_score ON jobs(score DESC, first_seen DESC);
CREATE INDEX IF NOT EXISTS jobs_active ON jobs(is_active);
CREATE INDEX IF NOT EXISTS jobs_deadline ON jobs(deadline);
CREATE TABLE IF NOT EXISTS job_sources(
 source TEXT NOT NULL, identity TEXT NOT NULL, job_id TEXT NOT NULL REFERENCES jobs(id),
 external_id TEXT, apply_url TEXT NOT NULL, last_seen TEXT NOT NULL,
 missing_count INTEGER NOT NULL DEFAULT 0, is_active INTEGER NOT NULL DEFAULT 1,
 PRIMARY KEY(source, identity)
);
CREATE INDEX IF NOT EXISTS sources_external ON job_sources(source, external_id);
CREATE INDEX IF NOT EXISTS sources_url ON job_sources(apply_url);
CREATE TABLE IF NOT EXISTS job_versions(
 id INTEGER PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id),
 created_at TEXT NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS companies(
 source TEXT PRIMARY KEY, last_success TEXT, last_failure TEXT,
 consecutive_failures INTEGER NOT NULL DEFAULT 0, bootstrapped INTEGER NOT NULL DEFAULT 0,
 last_job_seen TEXT, last_count INTEGER NOT NULL DEFAULT 0, average_response_time REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS scan_runs(
 id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, metrics TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts(
 id INTEGER PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id),
 event_key TEXT UNIQUE NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
 created_at TEXT NOT NULL, sent_at TEXT, attempts INTEGER NOT NULL DEFAULT 0,
 last_error TEXT
);
CREATE TABLE IF NOT EXISTS alert_history(
 id INTEGER PRIMARY KEY, alert_id INTEGER NOT NULL REFERENCES alerts(id),
 changed_at TEXT NOT NULL, actor TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT,
 before_payload TEXT NOT NULL, after_payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS alert_history_alert ON alert_history(alert_id,id);
CREATE TABLE IF NOT EXISTS applications(
 job_id TEXT PRIMARY KEY REFERENCES jobs(id), status TEXT NOT NULL DEFAULT 'New',
 application_date TEXT, recruiter TEXT, notes TEXT, next_action TEXT, next_action_date TEXT
);
CREATE TABLE IF NOT EXISTS application_history(
 id INTEGER PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id),
 changed_at TEXT NOT NULL, before_payload TEXT NOT NULL, after_payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS application_history_job ON application_history(job_id,id);
CREATE TABLE IF NOT EXISTS score_history(
 id INTEGER PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id),
 created_at TEXT NOT NULL, score INTEGER NOT NULL, explanation TEXT NOT NULL
);
"""


class Repository:
    def __init__(self, url: str):
        if not url.startswith("sqlite:///"):
            raise ValueError("This release supports sqlite:/// URLs only")
        path = url.removeprefix("sqlite:///")
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = path + ".lock"
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        if self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone():
            version = self.db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            if version is not None and version > SCHEMA_VERSION:
                self.db.close()
                raise ValueError("Database schema is newer than this application")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        version = self.db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        if version < 2:
            with self.db:
                rows = self.db.execute("""SELECT s.*,j.company FROM job_sources s
                    JOIN jobs j ON j.id=s.job_id""").fetchall()
                for row in rows:
                    identity = digest(
                        row["company"], row["external_id"] or canonical_url(row["apply_url"])
                    )
                    self.db.execute(
                        "UPDATE job_sources SET identity=? WHERE source=? AND identity=?",
                        (identity, row["source"], row["identity"]),
                    )
                self.db.execute("INSERT INTO schema_version VALUES(2)")
        if version < 3:
            with self.db:
                self.db.execute("INSERT INTO schema_version VALUES(3)")
        if version < 4:
            with self.db:
                self.db.execute("INSERT INTO schema_version VALUES(4)")

    def close(self) -> None:
        self.db.close()

    @contextmanager
    def transaction(self):
        with self.db:
            yield self

    def state(self, source: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM companies WHERE source=?", (source,)).fetchone()
        return dict(row) if row else {"bootstrapped": 0, "consecutive_failures": 0, "last_count": 0}

    def mark_success(self, source: str, count: int, duration: float) -> None:
        now = utcnow().isoformat()
        self.db.execute(
            """INSERT INTO companies(source,last_success,bootstrapped,last_job_seen,last_count,average_response_time)
            VALUES(?,?,1,?,?,?) ON CONFLICT(source) DO UPDATE SET
            last_success=excluded.last_success, bootstrapped=1, consecutive_failures=0,
            last_job_seen=COALESCE(excluded.last_job_seen,companies.last_job_seen),
            last_count=excluded.last_count,
            average_response_time=(companies.average_response_time+excluded.average_response_time)/2""",
            (source, now, now if count else None, count, duration),
        )

    def mark_failure(self, source: str) -> None:
        with self.db:
            self.record_failure(source)

    def record_failure(self, source: str) -> None:
        """Record failure inside the caller's transaction, without committing it."""
        self.db.execute(
            """INSERT INTO companies(source,last_failure,consecutive_failures) VALUES(?,?,1)
                ON CONFLICT(source) DO UPDATE SET last_failure=excluded.last_failure,
                consecutive_failures=companies.consecutive_failures+1""",
            (source, utcnow().isoformat()),
        )

    def get(self, job_id: str) -> Job:
        row = self.db.execute("SELECT payload FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return Job.model_validate_json(row[0])

    def application(self, job_id: str) -> Application:
        row = self.db.execute("SELECT * FROM applications WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return Application.model_validate(dict(row))

    def update_application(self, job_id: str, changes: dict) -> Application:
        allowed = set(Application.model_fields) - {"job_id"}
        if not changes or set(changes) - allowed:
            raise ValueError("Provide at least one editable application field")
        with FileLock(self.lock_path, timeout=0), self.transaction():
            previous = self.application(job_id)
            updated = Application.model_validate(previous.model_dump() | changes)
            if previous != updated:
                values = updated.model_dump(mode="json")
                self.db.execute(
                    """UPDATE applications SET status=?,application_date=?,recruiter=?,notes=?,
                    next_action=?,next_action_date=? WHERE job_id=?""",
                    tuple(
                        values[k]
                        for k in [
                            "status",
                            "application_date",
                            "recruiter",
                            "notes",
                            "next_action",
                            "next_action_date",
                            "job_id",
                        ]
                    ),
                )
                self.db.execute(
                    """INSERT INTO application_history(job_id,changed_at,before_payload,after_payload)
                    VALUES(?,?,?,?)""",
                    (
                        job_id,
                        utcnow().isoformat(),
                        previous.model_dump_json(),
                        updated.model_dump_json(),
                    ),
                )
            return updated

    def list_applications(
        self,
        status: ApplicationStatus | None = None,
        due_before: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("Invalid pagination")
        conditions, values = [], []
        if status is not None:
            conditions.append("a.status=?")
            values.append(ApplicationStatus(status).value)
        if due_before is not None:
            conditions.append("a.next_action_date<=? AND a.next_action IS NOT NULL")
            values.append(calendar_date(due_before).isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = self.db.execute(
            "SELECT a.job_id FROM applications a JOIN jobs j ON a.job_id=j.id"
            + where
            + " ORDER BY a.next_action_date IS NULL,a.next_action_date,j.score DESC,a.job_id LIMIT ? OFFSET ?",
            (*values, limit, offset),
        ).fetchall()
        return [self.application_details(row["job_id"]) for row in rows]

    def application_details(self, job_id: str) -> dict:
        job = self.get(job_id)
        return self.application(job_id).model_dump(mode="json") | {
            "company": job.company,
            "title": job.title,
            "location": job.location_normalized,
            "score": job.score_breakdown.total,
            "apply_url": job.apply_url,
            "job_active": job.is_active,
            "deadline": job.application_deadline.isoformat() if job.application_deadline else None,
        }

    def application_history(self, job_id: str) -> list[dict]:
        self.application(job_id)
        return [
            {
                "id": r["id"],
                "changed_at": r["changed_at"],
                "before": json.loads(r["before_payload"]),
                "after": json.loads(r["after_payload"]),
            }
            for r in self.db.execute(
                "SELECT * FROM application_history WHERE job_id=? ORDER BY id", (job_id,)
            )
        ]

    def _match(self, job: Job, identity: str) -> Job | None:
        row = self.db.execute(
            "SELECT job_id FROM job_sources WHERE source=? AND identity=?", (job.source, identity)
        ).fetchone()
        if not row:
            row = self.db.execute(
                """SELECT s.job_id FROM job_sources s JOIN jobs j ON j.id=s.job_id
                WHERE s.apply_url=? AND j.company=?
                AND (s.source<>? OR s.external_id IS NULL OR ? IS NULL OR s.external_id=?)
                LIMIT 1""",
                (
                    canonical_url(job.apply_url),
                    job.company_normalized,
                    job.source,
                    job.external_id,
                    job.external_id,
                ),
            ).fetchone()
        if row:
            return self.get(row[0])
        # Conservative fallback: never merge two different IDs on the same source.
        # Ambiguous matches and unknown locations stay distinct.
        if not job.location_normalized:
            return None
        candidates = self.db.execute(
            """SELECT id FROM jobs WHERE company=? AND title=? AND location=?
            AND id NOT IN (SELECT job_id FROM job_sources WHERE source=?)""",
            (job.company_normalized, job.title_normalized, job.location_normalized, job.source),
        ).fetchall()
        return self.get(candidates[0][0]) if len(candidates) == 1 else None

    def _write(self, job: Job) -> None:
        self.db.execute(
            """INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
            fingerprint=excluded.fingerprint,company=excluded.company,title=excluded.title,
            location=excluded.location,score=excluded.score,last_seen=excluded.last_seen,
            deadline=excluded.deadline,is_active=excluded.is_active,payload=excluded.payload""",
            (
                job.id,
                job.fingerprint,
                job.company_normalized,
                job.title_normalized,
                job.location_normalized,
                job.score_breakdown.total,
                job.first_seen.isoformat(),
                job.last_seen.isoformat(),
                job.application_deadline.isoformat() if job.application_deadline else None,
                int(job.is_active),
                job.model_dump_json(),
            ),
        )

    def upsert(self, incoming: Job) -> tuple[Job, str]:
        identity = source_identity(incoming)
        old = self._match(incoming, identity)
        event = "new"
        job = incoming
        if old:
            event = "unchanged"
            authoritative = (
                SOURCE_RANK[incoming.source_type] < SOURCE_RANK[old.source_type]
                or incoming.source == old.source
            )
            job = incoming if authoritative else old.model_copy(deep=True)
            job.id, job.fingerprint = old.id, old.fingerprint
            job.first_seen = old.first_seen
            job.last_seen = incoming.last_seen
            job.is_new = False
            changed = authoritative and any(
                getattr(old, f) != getattr(job, f) for f in CONTENT_FIELDS
            )
            job.date_updated = incoming.last_seen if changed else old.date_updated
            job.is_active = True
            job.is_expired = bool(job.application_deadline and job.application_deadline < utcnow())
            if not old.is_active:
                event = "reopened"
            elif changed:
                event = "updated"
            elif old.score_breakdown != job.score_breakdown:
                event = "rescored"
        self._write(job)
        self.db.execute(
            """INSERT INTO job_sources(source,identity,job_id,external_id,apply_url,last_seen)
            VALUES(?,?,?,?,?,?) ON CONFLICT(source,identity) DO UPDATE SET
            last_seen=excluded.last_seen,apply_url=excluded.apply_url,missing_count=0,is_active=1""",
            (
                incoming.source,
                identity,
                job.id,
                incoming.external_id,
                incoming.apply_url,
                incoming.last_seen.isoformat(),
            ),
        )
        self.db.execute("INSERT OR IGNORE INTO applications(job_id) VALUES(?)", (job.id,))
        if event != "unchanged":
            self.db.execute(
                "INSERT INTO job_versions(job_id,created_at,event,payload) VALUES(?,?,?,?)",
                (job.id, utcnow().isoformat(), event, job.model_dump_json()),
            )
            self.db.execute(
                "INSERT INTO score_history(job_id,created_at,score,explanation) VALUES(?,?,?,?)",
                (
                    job.id,
                    utcnow().isoformat(),
                    job.score_breakdown.total,
                    job.score_breakdown.model_dump_json(),
                ),
            )
        return job, event

    def update_scoring(self, job: Job) -> bool:
        """Persist a rule recalculation without pretending the source was scanned."""
        old = self.get(job.id)
        if (
            old.score_breakdown == job.score_breakdown
            and old.desk == job.desk
            and old.asset_class == job.asset_class
        ):
            return False
        self._write(job)
        self.db.execute(
            "INSERT INTO job_versions(job_id,created_at,event,payload) VALUES(?,?,?,?)",
            (job.id, utcnow().isoformat(), "rescored", job.model_dump_json()),
        )
        self.db.execute(
            "INSERT INTO score_history(job_id,created_at,score,explanation) VALUES(?,?,?,?)",
            (
                job.id,
                utcnow().isoformat(),
                job.score_breakdown.total,
                job.score_breakdown.model_dump_json(),
            ),
        )
        return True

    def update_derived_experience(self, job: Job) -> bool:
        """Record a reviewed derivation correction without refreshing the source.

        The caller owns the file lock and transaction, as for ``update_scoring``.
        Reject stale or unrelated edits instead of overwriting new observations.
        """
        old = self.get(job.id)
        job = Job.model_validate(job.model_dump())
        before, after = old.model_dump(), job.model_dump()
        changed = {key for key in before if before[key] != after[key]}
        if changed - {"minimum_experience_years", "experience_evidence", "score_breakdown"}:
            raise ValueError("Experience correction contains unrelated or stale job fields")
        if not changed:
            return False
        self._write(job)
        self.db.execute(
            "INSERT INTO job_versions(job_id,created_at,event,payload) VALUES(?,?,?,?)",
            (job.id, utcnow().isoformat(), "rescored", job.model_dump_json()),
        )
        self.db.execute(
            "INSERT INTO score_history(job_id,created_at,score,explanation) VALUES(?,?,?,?)",
            (
                job.id,
                utcnow().isoformat(),
                job.score_breakdown.total,
                job.score_breakdown.model_dump_json(),
            ),
        )
        return True

    def reconcile(self, source: str, seen: set[str], threshold: int) -> int:
        rows = self.db.execute("SELECT * FROM job_sources WHERE source=?", (source,)).fetchall()
        affected = set()
        for row in rows:
            if row["identity"] not in seen:
                misses = row["missing_count"] + 1
                self.db.execute(
                    "UPDATE job_sources SET missing_count=?,is_active=? WHERE source=? AND identity=?",
                    (misses, int(misses < threshold), source, row["identity"]),
                )
                affected.add(row["job_id"])
        closed = 0
        for job_id in affected:
            active = self.db.execute(
                "SELECT 1 FROM job_sources WHERE job_id=? AND is_active=1", (job_id,)
            ).fetchone()
            job = self.get(job_id)
            if not active and job.is_active:
                job.is_active, job.is_new = False, False
                job.date_updated = utcnow()
                self._write(job)
                self.db.execute(
                    "INSERT INTO job_versions(job_id,created_at,event,payload) VALUES(?,?,?,?)",
                    (job_id, utcnow().isoformat(), "closed", job.model_dump_json()),
                )
                closed += 1
        return closed

    def enqueue(self, job: Job, event: str) -> None:
        version = self.db.execute(
            "SELECT MAX(id) FROM job_versions WHERE job_id=?", (job.id,)
        ).fetchone()[0]
        self.db.execute(
            "INSERT OR IGNORE INTO alerts(job_id,event_key,created_at) VALUES(?,?,?)",
            (job.id, f"{job.id}:{event}:{version}", utcnow().isoformat()),
        )

    def pending(self) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM alerts WHERE status='pending' ORDER BY id").fetchall()

    def alert_status(self, event_key: str) -> str | None:
        row = self.db.execute(
            "SELECT status FROM alerts WHERE event_key=?", (event_key,)
        ).fetchone()
        return row[0] if row else None

    def enqueue_reminder(self, job_id: str, event_key: str) -> int:
        cursor = self.db.execute(
            "INSERT OR IGNORE INTO alerts(job_id,event_key,created_at) VALUES(?,?,?)",
            (job_id, event_key, utcnow().isoformat()),
        )
        return cursor.rowcount

    def set_alert(self, alert_id: int, status: str, error: str | None = None) -> None:
        """Scanner-owned transition; its caller holds the common writer lock."""
        status = AlertStatus(status)
        with self.db:
            previous = self.get_alert(alert_id)
            if previous["status"] == status and previous["last_error"] == error:
                return
            if status not in SYSTEM_TRANSITIONS.get(previous["status"], set()):
                raise ValueError("Invalid automatic alert transition")
            self.db.execute(
                "UPDATE alerts SET status=?,attempts=attempts+?,last_error=?,sent_at=? WHERE id=?",
                (
                    status.value,
                    int(status == AlertStatus.SENDING),
                    error,
                    utcnow().isoformat() if status == AlertStatus.SENT else previous["sent_at"],
                    alert_id,
                ),
            )
            self._record_alert_change(previous, "system", status.value, None)

    def get_alert(self, alert_id: int) -> dict:
        row = self.db.execute(
            """SELECT a.*,COALESCE((SELECT MAX(h.id) FROM alert_history h WHERE h.alert_id=a.id),0)
            AS revision FROM alerts a WHERE a.id=?""",
            (alert_id,),
        ).fetchone()
        if row is None:
            raise KeyError(alert_id)
        return dict(row)

    def alert_details(self, alert_id: int) -> dict:
        alert = self.get_alert(alert_id)
        job = self.get(alert["job_id"])
        return alert | {
            "company": job.company,
            "title": job.title,
            "url": job.apply_url,
            "job_active": job.is_active,
            "score": job.score_breakdown.total,
            "application_status": self.application(job.id).status.value,
        }

    def list_alerts(
        self,
        status: AlertStatus | None = None,
        all_states: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        if not 1 <= limit <= 1000 or offset < 0 or (all_states and status is not None):
            raise ValueError("Invalid alert filters or pagination")
        where, values = ("", []) if all_states else (" WHERE status IN ('unknown','sending')", [])
        if status is not None:
            where, values = " WHERE status=?", [AlertStatus(status).value]
        rows = self.db.execute(
            "SELECT id FROM alerts" + where + " ORDER BY id LIMIT ? OFFSET ?",
            (*values, limit, offset),
        ).fetchall()
        return {
            "summary": {
                row["status"]: row["count"]
                for row in self.db.execute(
                    "SELECT status,COUNT(*) count FROM alerts GROUP BY status"
                )
            },
            "matching": self.db.execute("SELECT COUNT(*) FROM alerts" + where, values).fetchone()[
                0
            ],
            "alerts": [self.alert_details(row["id"]) for row in rows],
        }

    def _record_alert_change(
        self, previous: dict, actor: str, decision: str, reason: str | None
    ) -> None:
        after = self.get_alert(previous["id"])
        # The history row ID is the revision; snapshots contain only persisted alert fields.
        self.db.execute(
            """INSERT INTO alert_history(alert_id,changed_at,actor,decision,reason,before_payload,after_payload)
            VALUES(?,?,?,?,?,?,?)""",
            (
                previous["id"],
                utcnow().isoformat(),
                actor,
                decision,
                reason,
                json.dumps({k: v for k, v in previous.items() if k != "revision"}),
                json.dumps({k: v for k, v in after.items() if k != "revision"}),
            ),
        )

    def resolve_alert(
        self, alert_id: int, decision: AlertDecision, revision: int, reason: str
    ) -> dict:
        decision = AlertDecision(decision)
        reason = reason.strip()
        if not reason or len(reason) > 2000 or revision < 0:
            raise ValueError("Provide a reason (1–2000 characters) and a nonnegative revision")
        with FileLock(self.lock_path, timeout=0), self.transaction():
            previous = self.get_alert(alert_id)
            if previous["revision"] != revision:
                raise ValueError("Alert changed since inspection; show it again before deciding")
            status = resolved_status(previous["status"], decision)
            # Manual receipt confirmation is not a new transport acknowledgement.
            # Keep sent_at unknown if the actual delivery instant was never established.
            self.db.execute("UPDATE alerts SET status=? WHERE id=?", (status.value, alert_id))
            self._record_alert_change(previous, "operator", decision.value, reason)
            return self.alert_details(alert_id)

    def alert_history(self, alert_id: int) -> list[dict]:
        self.get_alert(alert_id)
        return [
            {
                "revision": r["id"],
                "changed_at": r["changed_at"],
                "actor": r["actor"],
                "decision": r["decision"],
                "reason": r["reason"],
                "before": json.loads(r["before_payload"]),
                "after": json.loads(r["after_payload"]),
            }
            for r in self.db.execute(
                "SELECT * FROM alert_history WHERE alert_id=? ORDER BY id", (alert_id,)
            )
        ]

    def list_jobs(self, min_score: int = 0, new_only: bool = False) -> list[Job]:
        rows = self.db.execute(
            "SELECT payload FROM jobs WHERE score>=? ORDER BY score DESC,first_seen DESC",
            (min_score,),
        )
        jobs = [Job.model_validate_json(r[0]) for r in rows]
        return [j for j in jobs if j.is_new] if new_only else jobs

    def stats(self) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT COUNT(*) total, SUM(is_active) active, SUM(score>=70) high_priority FROM jobs"
        ).fetchone()
        return {
            **dict(row),
            "sources": [dict(r) for r in self.db.execute("SELECT * FROM companies")],
            "alerts": [
                dict(r)
                for r in self.db.execute("SELECT status,COUNT(*) count FROM alerts GROUP BY status")
            ],
        }

    def record_scan(self, metrics: dict) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO scan_runs(created_at,metrics) VALUES(?,?)",
                (utcnow().isoformat(), json.dumps(metrics)),
            )
