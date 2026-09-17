import csv
from pathlib import Path

from trading_radar.storage import Repository


def safe_cell(value: object) -> str:
    text = str(value) if value is not None else ""
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def export_csv(repo: Repository, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    jobs = repo.list_jobs()
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "company",
                "role",
                "location",
                "score",
                "priority",
                "date_posted",
                "first_seen",
                "deadline",
                "source",
                "apply_url",
                "status",
                "is_active",
                "job_id",
                "application_date",
                "recruiter",
                "notes",
                "next_action",
                "next_action_date",
            ]
        )
        for job in jobs:
            application = repo.application(job.id)
            writer.writerow(
                [
                    safe_cell(v)
                    for v in [
                        job.company,
                        job.title,
                        job.location_normalized,
                        job.score_breakdown.total,
                        job.score_breakdown.priority,
                        job.date_posted,
                        job.first_seen,
                        job.application_deadline,
                        job.source,
                        job.apply_url,
                        application.status.value,
                        job.is_active,
                        job.id,
                        application.application_date,
                        application.recruiter,
                        application.notes,
                        application.next_action,
                        application.next_action_date,
                    ]
                ]
            )
    temporary.replace(path)
    return len(jobs)
