"""Plan or explicitly probe two bounded public Workday queries, without importing jobs."""

import argparse
import asyncio
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_radar.config import Config, load_config
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import utcnow
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.workday import (
    WorkdayCollector,
    WorkdayOptions,
    comparable_title,
    external_path,
    workday_base,
)

MAX_RESULTS = 200
MAX_DETAILS = 12
MAX_SECONDS = 180
MAX_BASELINE_ROWS = 100_000


def validate(
    config: Config,
    source: str,
    terms: list[str],
    *,
    applied_facets: dict[str, list[str]] | None = None,
):
    company = config.companies.get(source)
    if company is None or not company.enabled or company.ats != "workday":
        raise ValueError("Source must be an enabled configured Workday source")
    if not 1 <= len(terms) <= 2 or any(
        not isinstance(t, str) or not t.strip() or len(t) > 100 for t in terms
    ):
        raise ValueError("One or two nonempty terms of at most 100 characters are required")
    if len({t.strip().casefold() for t in terms}) != len(terms):
        raise ValueError("Terms must be distinct")
    company = company.model_copy(deep=True)
    if applied_facets is not None:
        # Explicit probe filters replace the configured scope, without mutating it.
        company.options["applied_facets"] = applied_facets
    company.request_interval = max(2, company.request_interval)
    company.options.update(
        search_terms=[t.strip() for t in terms],
        max_results_per_query=MAX_RESULTS,
        max_details=MAX_DETAILS,
        max_scan_seconds=MAX_SECONDS,
        conditional_details=False,
    )
    options = WorkdayOptions(**company.options)
    company.options["applied_facets"] = options.applied_facets
    workday_base(company)
    return company


def database_path(config: Config) -> Path:
    url = config.settings.database_url
    if not url.startswith("sqlite:///") or url in {"sqlite:///", "sqlite:///:memory:"}:
        raise ValueError("An existing SQLite database is required")
    path = Path(url.removeprefix("sqlite:///")).resolve()
    if not path.is_file():
        raise ValueError("Database does not exist")
    return path


def baseline(config: Config, source: str, site: str) -> dict[str, Any]:
    """Existing paths and latest stored observation, from one read-only snapshot."""

    def path_from_url(url: object) -> str:
        if not isinstance(url, str) or not url.startswith(site + "/job/"):
            raise ValueError("Stored source URL does not match the configured Workday site")
        return external_path(url[len(site) :])

    known: set[str] = set()
    observed: list[tuple[str, datetime]] = []
    with closing(sqlite3.connect(database_path(config).as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        rows = db.execute(
            "SELECT apply_url,last_seen FROM job_sources WHERE source=? LIMIT ?",
            (source, MAX_BASELINE_ROWS + 1),
        ).fetchall()
        if len(rows) > MAX_BASELINE_ROWS:
            raise ValueError("Stored baseline exceeds row limit")
        for url, last_seen in rows:
            path = path_from_url(url)
            stamp = datetime.fromisoformat(last_seen)
            if stamp.tzinfo is None:
                raise ValueError("Stored observation timestamp must have a timezone")
            known.add(path)
            observed.append((path, stamp))
        # Include canonical jobs even when another source owns their latest payload.
        rows = db.execute("SELECT payload FROM jobs LIMIT ?", (MAX_BASELINE_ROWS + 1,)).fetchall()
        if len(rows) > MAX_BASELINE_ROWS:
            raise ValueError("Stored jobs exceed row limit")
        for (payload,) in rows:
            job = json.loads(payload)
            if not isinstance(job, dict):
                raise ValueError("Invalid stored job")
            for key in ("apply_url", "source_url"):
                url = job.get(key)
                if isinstance(url, str) and url.startswith(site + "/job/"):
                    known.add(path_from_url(url))
        latest = max((stamp for _, stamp in observed), default=None)
    return {
        "read_at": utcnow().isoformat(),
        "latest_observation_at": latest.isoformat() if latest else None,
        "known_paths": sorted(known),
        "meaning": "All stored known source paths; latest timestamp is per job, not a scan batch. Not a current full trading search or market inventory",
    }


def build_plan(
    config: Config,
    source: str,
    terms: list[str],
    *,
    applied_facets: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    company = validate(config, source, terms, applied_facets=applied_facets)
    site, _ = workday_base(company)
    return {
        "format_version": 1,
        "mode": "offline-plan",
        "created_at": utcnow().isoformat(),
        "source": source,
        "terms": company.options["search_terms"],
        "applied_facets": company.options["applied_facets"],
        "limits": {
            "results_per_query": MAX_RESULTS,
            "supplemental_details": MAX_DETAILS,
            "seconds": MAX_SECONDS,
            "http_timeout": min(20, config.settings.timeout),
            "retries": 0,
            "request_interval": company.request_interval,
        },
        "baseline": baseline(config, source, site),
    }


async def probe(config: Config, plan: dict[str, Any], *, transport=None) -> tuple[dict, list[dict]]:
    """Explicit network entry point. Never persist or import into the application database."""
    source, terms = plan["source"], plan["terms"]
    # A saved plan pins its filter scope even if the configuration changes later.
    # Older plans without this field retain the configured scope for compatibility.
    company = validate(config, source, terms, applied_facets=plan.get("applied_facets"))
    # Read afresh: programmatic callers cannot inject arbitrary baseline paths.
    reference = baseline(config, source, workday_base(company)[0])
    known = set(reference["known_paths"])
    report: dict[str, Any] = {
        "format_version": 1,
        "mode": "network",
        "source": source,
        "applied_facets": company.options["applied_facets"],
        "started_at": utcnow().isoformat(),
        "status": "incomplete",
        "queries": [],
        "baseline": reference,
        "limits": plan["limits"],
        "details": [],
        "exhaustive": False,
        "database_imported": False,
    }
    details: list[dict] = []
    detail_ids: set[str | None] = set()
    selected: dict[str, dict] = {}
    http = HTTPClient(timeout=min(config.settings.timeout, 20), retries=0, transport=transport)
    collector = WorkdayCollector(source, company, http)
    stage = "search"
    try:
        async with asyncio.timeout(MAX_SECONDS):
            for term in terms:
                query: dict[str, Any] = {"term": term, "status": "incomplete"}
                report["queries"].append(query)
                rows = await collector._search(term)
                targets = {p: r for p, r in rows.items() if collector.selected(r["title"])}
                query.update(
                    status="ok",
                    raw_count=len(rows),
                    selected_count=len(targets),
                    known_paths=sorted(set(targets) & known),
                    unseen_paths=sorted(set(targets) - known),
                )
                for path, row in targets.items():
                    if path in selected and comparable_title(
                        selected[path]["title"]
                    ) != comparable_title(row["title"]):
                        raise SourceUnavailable("Workday title changed across queries")
                    selected[path] = row
                if len(set(selected) - known) > MAX_DETAILS:
                    stage = "detail_limit"
                    raise SourceUnavailable("Supplemental detail limit exceeded")
            stage = "detail"
            for path in sorted(set(selected) - known):
                raw = await collector._detail(path, selected[path])
                if raw.external_id in detail_ids:
                    raise SourceUnavailable("Workday repeated a detail identifier")
                detail_ids.add(raw.external_id)
                job = score_job(normalize(raw), config.keywords)
                details.append(raw.model_dump(mode="json"))
                report["details"].append(
                    {
                        "path": path,
                        "id": raw.external_id,
                        "title": raw.title,
                        "url": raw.apply_url,
                        "score": job.score_breakdown.total,
                        "reasons": job.score_breakdown.reasons,
                        "exclusions": job.score_breakdown.exclusions,
                        "read_at": utcnow().isoformat(),
                    }
                )
            report["status"] = "ok"
    except (SourceUnavailable, ValueError, TimeoutError) as exc:
        # Do not record raw exception messages, response headers, cookies or config secrets.
        code = type(exc).__name__
        if isinstance(exc, TimeoutError):
            code = "time_limit"
        elif isinstance(exc, SourceUnavailable):
            message = str(exc)
            if "result limit" in message:
                code = "result_limit"
            elif stage == "detail_limit":
                code = "detail_limit"
            elif "network timeout or transport error" in message:
                code = "transport_error"
            elif "robots" in message:
                code = "robots_policy"
            elif "repeated a detail identifier" in message:
                code = "duplicate_detail_id"
        report["error"] = {
            "stage": stage,
            "code": code,
            "message": "Probe incomplete; no database import performed",
        }
    finally:
        await http.close()
    report.update(
        finished_at=utcnow().isoformat(),
        requests=http.counts[source],
        unique_selected=len(selected),
        supplemental_details_read=len(details),
    )
    return report, details


def output_directory(path: Path, config: Config) -> Path:
    """Require a new directory with no symlink/junction ancestors or existing targets."""
    absolute = path.absolute()
    roots = [Path(f"data/discovery/{lot}").absolute() for lot in ("lot27", "lot30")]
    root = next((r for r in roots if absolute.is_relative_to(r) and absolute != r), None)
    if root is None:
        raise ValueError("Output must be a new directory under data/discovery/lot27 or lot30")
    for parent in (absolute, *absolute.parents):
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise ValueError("Output cannot use symlink or junction paths")
    resolved = absolute.resolve()
    if not resolved.is_relative_to(root.resolve()) or resolved == root.resolve():
        raise ValueError("Output escapes its permitted discovery directory")
    if absolute.exists():
        raise ValueError("Output directory already exists; evidence is immutable")
    database = database_path(config)
    protected = {
        Path(str(database) + suffix) for suffix in ("", "-wal", "-shm", "-journal", ".lock")
    }
    if any(p == resolved or p.is_relative_to(resolved) for p in protected):
        raise ValueError("Output cannot contain database or sidecars")
    return resolved


def write_artifact(directory: Path, name: str, value: object) -> dict[str, Any]:
    content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    # Exclusive create prevents overwriting files, including hardlink aliases.
    with (directory / name).open("xb") as stream:
        stream.write(content)
    return {"file": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def parse_facets(arguments: list[str] | None) -> dict[str, list[str]] | None:
    """Group explicit public facet identifiers; omit to inherit configured filters."""
    if arguments is None:
        return None
    facets: dict[str, list[str]] = {}
    for argument in arguments:
        key, separator, value = argument.partition("=")
        if not separator or value in facets.get(key, []):
            raise ValueError("Invalid or duplicate facet argument")
        facets.setdefault(key, []).append(value)
    return WorkdayOptions(applied_facets=facets).applied_facets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", action="store_true")
    parser.add_argument("--source", default="citi")
    parser.add_argument("--term", action="append")
    parser.add_argument(
        "--facet",
        action="append",
        metavar="KEY=VALUE",
        help="Public portal facet identifier; repeat for multiple values. Replaces configured filters.",
    )
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config_dir)
        destination = output_directory(args.output_dir, config)
        plan = build_plan(
            config,
            args.source,
            args.term or ["repo", "securities finance"],
            applied_facets=parse_facets(args.facet),
        )
        destination.mkdir(parents=True, exist_ok=False)
        metadata = [write_artifact(destination, "plan.json", plan)]
        if args.network:
            report, details = asyncio.run(probe(config, plan))
            metadata.append(write_artifact(destination, "details.json", details))
            report["artifacts"] = metadata
            metadata.append(write_artifact(destination, "report.json", report))
        else:
            report = {"mode": "offline-plan", "status": "planned"}
        write_artifact(destination, "manifest.json", {"artifacts": metadata})
        print(
            json.dumps(
                {
                    "mode": report["mode"],
                    "status": report["status"],
                    "output_dir": str(args.output_dir),
                }
            )
        )
        return int(report["status"] == "incomplete")
    except (ValueError, OSError, sqlite3.Error, SourceUnavailable):
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "Invalid configuration, baseline or output; probe stopped",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
