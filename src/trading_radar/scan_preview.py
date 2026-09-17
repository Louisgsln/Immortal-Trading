"""Run an ordinary scan against a disposable, verified database snapshot."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from trading_radar.backups import create_backup, database_path, restore_backup
from trading_radar.collectors import Collector
from trading_radar.config import Config
from trading_radar.http import HTTPClient
from trading_radar.models import Job, utcnow
from trading_radar.scanner import scan
from trading_radar.storage import Repository

MAX_JOBS = 5_000
MAX_CHANGES = 10_000
MAX_PAYLOAD = 2_000_000
# Explicit business fields keep technical timestamps, raw payloads and duplicate
# normalized/raw labels out of the report. Report names only, never field values.
CHANGE_FIELDS = (
    "application_deadline",
    "apply_url",
    "asset_class",
    "city",
    "company",
    "country",
    "date_posted",
    "description_text",
    "desk",
    "employment_type",
    "experience_evidence",
    "expected_start_date",
    "is_active",
    "is_expired",
    "location_normalized",
    "location_tier",
    "minimum_experience_years",
    "programme_type",
    "region",
    "remote",
    "role_hint",
    "score_breakdown",
    "seniority",
    "seniority_hint",
    "title",
)
MESSAGES = {
    "invalid_config": "Une base SQLite locale sur disque est nécessaire.",
    "snapshot_failed": "La copie de la base n’a pas pu être vérifiée. Aucun aperçu fourni.",
    "limit_exceeded": "Une limite de l’aperçu est dépassée. Aucun aperçu partiel fourni.",
    "invalid_data": "Une offre conservée contient des données incohérentes.",
    "scan_failed": "L’aperçu de collecte n’a pas pu être terminé.",
}


class PreviewError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(MESSAGES[code])


def _jobs(repo: Repository) -> dict[str, Job]:
    if repo.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] > MAX_JOBS:
        raise PreviewError("limit_exceeded")
    result = {}
    for identifier, score, active, size, payload in repo.db.execute(
        "SELECT id,score,is_active,length(payload),substr(payload,1,?) FROM jobs",
        (MAX_PAYLOAD + 1,),
    ):
        if not isinstance(size, int) or size > MAX_PAYLOAD:
            raise PreviewError("limit_exceeded")
        try:
            job = Job.model_validate_json(payload)
        except ValueError:
            raise PreviewError("invalid_data") from None
        if (job.id, job.score_breakdown.total, int(job.is_active)) != (identifier, score, active):
            raise PreviewError("invalid_data")
        result[job.id] = job
    return result


def _changes(repo: Repository, start: int, previous: dict[str, Job]) -> list[dict]:
    count = repo.db.execute("SELECT COUNT(*) FROM job_versions WHERE id>?", (start,)).fetchone()[0]
    if count > MAX_CHANGES:
        raise PreviewError("limit_exceeded")
    changes = []
    for identifier, event, size, payload in repo.db.execute(
        "SELECT job_id,event,length(payload),substr(payload,1,?) "
        "FROM job_versions WHERE id>? ORDER BY id",
        (MAX_PAYLOAD + 1, start),
    ):
        if not isinstance(size, int) or size > MAX_PAYLOAD:
            raise PreviewError("limit_exceeded")
        try:
            job = Job.model_validate_json(payload)
        except ValueError:
            raise PreviewError("invalid_data") from None
        if job.id != identifier:
            raise PreviewError("invalid_data")
        old = previous.get(identifier)
        changes.append(
            {
                "event": event,
                "id": identifier,
                "company": job.company,
                "title": job.title,
                "source": job.source,
                "apply_url": job.apply_url,
                "before_score": old.score_breakdown.total if old else None,
                "after_score": job.score_breakdown.total,
                "before_active": old.is_active if old else None,
                "after_active": job.is_active,
                "changed_fields": (
                    sorted(
                        field
                        for field in CHANGE_FIELDS
                        if getattr(old, field) != getattr(job, field)
                    )
                    if old
                    else []
                ),
            }
        )
        previous[identifier] = job
    return changes


async def preview_scan(
    config: Config,
    *,
    company: str | None = None,
    source: str | None = None,
    due_only: bool = False,
    collectors: dict[str, Collector] | None = None,
    http: HTTPClient | None = None,
) -> dict:
    """Collect live data without persisting results or sending notifications.

    New job identifiers belong to this simulation. The report is an observation,
    not an import plan: a subsequent real scan collects and validates data again.
    Existing committed WAL content is included; source tables and configuration
    are never written. All writable repositories and lock files are temporary.
    """
    result: dict = {
        "format_version": 1,
        "generated_at": utcnow().isoformat(),
        "read_only": True,
        "ephemeral_new_ids": True,
        "status": "ok",
        "error": None,
        "metrics": None,
        "changes": [],
    }
    stage = "invalid_config"
    try:
        source_path = database_path(config.settings.database_url)
        # lexists distinguishes a dangling link from an absent, fresh database.
        if "\x00" in config.settings.database_url:
            raise PreviewError("invalid_config")
        stage = "snapshot_failed"
        with TemporaryDirectory(prefix="radar-scan-preview-") as directory:
            temporary = Path(directory)
            target = temporary / "preview.sqlite3"
            if os.path.lexists(config.settings.database_url.removeprefix("sqlite:///")):
                archive = temporary / "snapshot.zip"
                manifest = create_backup(source_path, archive)
                if manifest["tables"]["jobs"] > MAX_JOBS:
                    raise PreviewError("limit_exceeded")
                restore_backup(archive, target, protected=source_path)
            cloned = config.model_copy(deep=True)
            cloned.settings.database_url = f"sqlite:///{target}"
            cloned.settings.alerts_enabled = False
            cloned.settings.deadline_reminders_enabled = False
            repo = Repository(cloned.settings.database_url)
            try:
                before = _jobs(repo)
                start = repo.db.execute("SELECT COALESCE(MAX(id),0) FROM job_versions").fetchone()[
                    0
                ]
                stage = "scan_failed"
                metrics = await scan(
                    cloned,
                    repo,
                    company=company,
                    source=source,
                    due_only=due_only,
                    collectors=collectors,
                    http=http,
                )
                _jobs(repo)
                changes = _changes(repo, start, before)
                result.update(
                    status="incomplete" if metrics.failed else "ok",
                    metrics=metrics.model_dump(mode="json"),
                    changes=changes,
                )
            finally:
                repo.close()
    except Exception as exc:
        code = exc.code if isinstance(exc, PreviewError) else stage
        result.update(
            status="error",
            error={"code": code, "message": MESSAGES[code]},
            metrics=None,
            changes=[],
        )
    return result
