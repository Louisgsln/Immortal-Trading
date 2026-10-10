"""Compare an independently reviewed offer reference against one local SQLite snapshot."""

import json
from pathlib import Path

from trading_radar.bofa_campus import BofACampusOptions
from trading_radar.config import Config
from trading_radar.goldman import GoldmanOptions
from trading_radar.greenhouse_filtered import GreenhouseOptions
from trading_radar.jefferies_campus import JefferiesCampusOptions
from trading_radar.lever_filtered import LeverOptions
from trading_radar.models import utcnow
from trading_radar.nomura import NomuraOptions
from trading_radar.programmes import programme_company
from trading_radar.score_audit import job_snapshot, snapshot_jobs
from trading_radar.search_scope import SearchOptions
from trading_radar.selection import rejection_reason
from trading_radar.societe_generale import SGOptions
from trading_radar.workday import WorkdayOptions

OPTIONS = {
    "bofa_campus": BofACampusOptions,
    "jefferies_campus": JefferiesCampusOptions,
    "morgan_stanley_campus": SearchOptions,
    "nomura": NomuraOptions,
    "oracle": SearchOptions,
    "goldman": GoldmanOptions,
    "greenhouse_filtered": GreenhouseOptions,
    "workday": WorkdayOptions,
    "lever_filtered": LeverOptions,
    "societe_generale": SGOptions,
}


def read_reference(path: Path, config: Config) -> list[dict[str, str]]:
    # Read a bounded amount even if the file grows after stat.
    with path.open("rb") as stream:
        content = stream.read(256_001)
    if len(content) > 256_000:
        raise ValueError("Reference exceeds 256000 bytes")
    payload = json.loads(content)
    if not isinstance(payload, list) or not 1 <= len(payload) <= 2000:
        raise ValueError("Provide 1 to 2000 independently verified offers")
    seen = set()
    for item in payload:
        if not isinstance(item, dict) or set(item) != {"source", "external_id", "title"}:
            raise ValueError("Each reference offer requires source, external_id and title")
        if any(
            not isinstance(value, str) or not value.strip() or len(value) > 500
            for value in item.values()
        ):
            raise ValueError("Reference fields must contain 1 to 500 characters")
        if item["source"] not in config.companies:
            raise ValueError("Reference contains an unconfigured source")
        key = (item["source"], item["external_id"])
        if key in seen:
            raise ValueError("Duplicate reference offer")
        seen.add(key)
    return payload


def coverage_report(config: Config, reference: Path) -> dict:
    expected = read_reference(reference, config)
    with job_snapshot(config) as db:
        jobs = {job.id: job for job in snapshot_jobs(db)}
        if db.execute("SELECT COUNT(*) FROM job_sources").fetchone()[0] > 50_000:
            raise ValueError("Source mapping limit exceeded")
        associations = {}
        for source, identifier, job_id in db.execute(
            "SELECT source,external_id,job_id FROM job_sources WHERE external_id IS NOT NULL"
        ):
            if job_id not in jobs or (source, identifier) in associations:
                raise ValueError("Ambiguous or invalid source identity")
            associations[source, identifier] = job_id
        entries: list[dict] = []
        for item in expected:
            company = programme_company(config.companies[item["source"]], config.settings)
            job_id = associations.get((item["source"], item["external_id"]))
            job = jobs.get(job_id) if job_id else None
            options_type = OPTIONS.get(company.ats)
            reason = (
                rejection_reason(item["title"], options_type(**company.options))
                if options_type
                else "not_measured"
            )
            entries.append(
                {
                    **item,
                    "found": job is not None,
                    "active": job.is_active if job else None,
                    "score": job.score_breakdown.total if job else None,
                    "source_enabled": company.enabled,
                    "title_filter_rejection": reason,
                }
            )
    found = sum(entry["found"] for entry in entries)
    return {
        "format_version": 1,
        "generated_at": utcnow().isoformat(),
        "read_only": True,
        "reference_count": len(entries),
        "found": found,
        "missing": len(entries) - found,
        "reference_coverage_percent": round(100 * found / len(entries), 1),
        "scope": "provided_reference_only",
        "diagnostic_scope": "title_only",
        "entries": entries,
    }
