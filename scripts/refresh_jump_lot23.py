"""Archive one public Jump catalogue, or replay it without network/database writes."""

import argparse
import asyncio
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import API, GreenhouseOptions, parse_board
from trading_radar.http import HTTPClient
from trading_radar.models import Collection, RawJob, utcnow
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job

SOURCE = "jump_trading"
ROOT = Path("data/discovery/lot23/jump")
BASELINE = Path("data/discovery/lot12/2d6ba1702416.html")


def validate_output(root: Path) -> None:
    """Keep proof writes in discovery and away from database aliases."""
    allowed = (Path.cwd() / "data" / "discovery").resolve()
    resolved = root.resolve()
    if resolved == allowed or not resolved.is_relative_to(allowed) or root.is_symlink():
        raise ValueError("Output must be a dedicated directory under data/discovery")
    url = load_config().settings.database_url
    if not url.startswith("sqlite:///"):
        raise ValueError("This audit requires a SQLite database")
    database = Path(url.removeprefix("sqlite:///")).resolve()
    protected = [
        Path(str(database) + suffix) for suffix in ("", "-wal", "-shm", "-journal", ".lock")
    ]
    for name in (
        "catalogue.json",
        "capture.json",
        "capture-failure.json",
        "analysis.json",
        "collection.json",
    ):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(allowed):
            raise ValueError("Output aliases outside discovery are forbidden")
        for target in protected:
            if path.resolve() == target or (
                path.exists() and target.exists() and path.samefile(target)
            ):
                raise ValueError("Output must not alias a database or its sidecars")


def write_json(path: Path, payload: object) -> None:
    validate_output(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_capture(path: Path) -> tuple[dict, dict]:
    """Verify the public archive and its provenance before parsing/replaying it."""
    content = path.read_bytes()
    manifest = json.loads((path.parent / "capture.json").read_bytes())
    expected_url = API + "jumptrading/jobs?content=true"
    if (
        manifest.get("source") != SOURCE
        or manifest.get("url") != expected_url
        or manifest.get("sha256") != hashlib.sha256(content).hexdigest()
        or manifest.get("bytes") != len(content)
    ):
        raise ValueError("Capture provenance, checksum or byte count mismatch")
    captured_at = datetime.fromisoformat(manifest["captured_at"])
    if captured_at.tzinfo is None:
        raise ValueError("Capture timestamp must have a timezone")
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError("Expected a public Greenhouse JSON object")
    return payload, manifest


async def capture(root: Path) -> Path:
    validate_output(root)
    root.mkdir(parents=True, exist_ok=True)
    if (root / "catalogue.json").exists():
        raise ValueError("Archive already exists; replay it or choose another --output directory")
    config = load_config()
    company = config.companies[SOURCE]
    url = API + company.tenant + "/jobs?content=true"
    http = HTTPClient(timeout=config.settings.timeout, retries=0)
    events = []
    body = None

    async def record(response: httpx.Response) -> None:
        nonlocal body
        events.append(
            {
                "at": utcnow().isoformat(),
                "url": str(response.request.url),
                "status": response.status_code,
            }
        )
        if str(response.request.url) == url and response.status_code == 200:
            body = await response.aread()

    http.client.event_hooks["response"].append(record)
    started = utcnow().isoformat()
    try:
        await http.get_json(url, company.request_interval, SOURCE)
    except Exception as exc:
        write_json(
            root / "capture-failure.json",
            {
                "started_at": started,
                "failed_at": utcnow().isoformat(),
                "url": url,
                "error": str(exc),
                "responses": events,
                "requests": http.counts[SOURCE],
                "database_writes": False,
            },
        )
        raise
    finally:
        await http.close()
    if body is None:
        raise ValueError("Successful public JSON response body was not captured")
    path = root / "catalogue.json"
    with path.open("xb") as stream:
        stream.write(body)
    write_json(
        root / "capture.json",
        {
            "source": SOURCE,
            "url": url,
            "started_at": started,
            "captured_at": utcnow().isoformat(),
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "requests": http.counts[SOURCE],
            "responses": events,
            "database_writes": False,
            "notifications": False,
        },
    )
    return path


def external_ids(jobs: list[RawJob]) -> set[str]:
    identifiers: set[str] = set()
    for job in jobs:
        if job.external_id is None:
            raise ValueError("Verified Jump jobs must have an external identifier")
        identifiers.add(job.external_id)
    return identifiers


def replay(path: Path, root: Path) -> dict:
    validate_output(root)
    config = load_config()
    company = config.companies[SOURCE]
    options = GreenhouseOptions.model_validate(company.options)
    content = path.read_bytes()
    payload, manifest = load_capture(path)
    raws = parse_board(payload, SOURCE, company, options)
    baseline_content = BASELINE.read_bytes()
    baseline = json.loads(baseline_content)
    baseline_raws = parse_board(baseline, SOURCE, company, options)
    current_ids = {str(row["id"]) for row in payload["jobs"]}
    baseline_ids = {str(row["id"]) for row in baseline["jobs"]}
    retained_ids = external_ids(raws)
    baseline_retained = external_ids(baseline_raws)
    database_url = config.settings.database_url
    if not database_url.startswith("sqlite:///"):
        raise ValueError("Read-only audit requires a SQLite database")
    database_path = Path(database_url.removeprefix("sqlite:///")).resolve()
    database = sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True)
    try:
        database.execute("PRAGMA query_only=ON")
        database.execute("BEGIN")
        stored = {
            external: {"id": identifier, "score": score, "active": bool(active)}
            for external, identifier, score, active in database.execute(
                "SELECT s.external_id,j.id,j.score,s.is_active FROM job_sources s "
                "JOIN jobs j ON j.id=s.job_id WHERE s.source=?",
                (SOURCE,),
            )
        }
    finally:
        database.close()
    jobs: list[dict[str, Any]] = []
    for raw in raws:
        job = score_job(normalize(raw), config.keywords)
        previous = stored.get(raw.external_id)
        jobs.append(
            {
                "external_id": raw.external_id,
                "id": job.id,
                "title": job.title,
                "location": job.location,
                "apply_url": job.apply_url,
                "minimum_experience_years": job.minimum_experience_years,
                "role_hint": job.role_hint,
                "score": job.score_breakdown.total,
                "exclusions": job.score_breakdown.exclusions,
                "previous_database": previous,
                "score_delta": job.score_breakdown.total - previous["score"] if previous else None,
            }
        )
    report = {
        "analyzed_at": utcnow().isoformat(),
        "source": SOURCE,
        "archive": str(path),
        "archive_sha256": hashlib.sha256(content).hexdigest(),
        "captured_at": manifest["captured_at"],
        "baseline": str(BASELINE),
        "baseline_sha256": hashlib.sha256(baseline_content).hexdigest(),
        "catalogue_count": len(current_ids),
        "baseline_catalogue_count": len(baseline_ids),
        "catalogue_added_ids": sorted(current_ids - baseline_ids),
        "catalogue_missing_ids": sorted(baseline_ids - current_ids),
        "selected_count": len(raws),
        "baseline_selected_with_current_code": len(baseline_raws),
        "selected_added_ids": sorted(retained_ids - baseline_retained),
        "selected_missing_ids": sorted(baseline_retained - retained_ids),
        "database_source_count": len(stored),
        "new_to_database_ids": sorted(retained_ids - stored.keys()),
        "database_ids_not_selected": sorted(stored.keys() - retained_ids),
        "high_priority": sum(job["score"] >= 70 for job in jobs),
        "relevant": sum(job["score"] >= 55 for job in jobs),
        "collection_complete": False,
        "absence_can_close": False,
        "database_writes": False,
        "notifications": False,
        "jobs": jobs,
    }
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "analysis.json", report)
    write_json(
        root / "collection.json",
        Collection(jobs=raws, complete=False, requests=0).model_dump(mode="json"),
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--network", action="store_true", help="Explicitly fetch one public catalogue"
    )
    parser.add_argument("--output", type=Path, default=ROOT)
    parser.add_argument("--archive", type=Path, help="Replay this archive without network")
    args = parser.parse_args()
    if args.network and args.archive:
        parser.error("--network and --archive are mutually exclusive")
    archive = (
        asyncio.run(capture(args.output))
        if args.network
        else args.archive or args.output / "catalogue.json"
    )
    result = replay(archive, args.output)
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "jobs"},
            ensure_ascii=False,
            indent=2,
        )
    )
