"""Read-only coverage audit from saved public boards; optional two-source access probe."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

import httpx

from trading_radar.config import load_config
from trading_radar.greenhouse_filtered import GreenhouseOptions, parse_board
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import utcnow
from trading_radar.normalizer import normalize, plain_text
from trading_radar.scoring import score_job

ROOT = Path("data/discovery/lot21/coverage")
BOARDS = {
    "jump_trading": Path("data/discovery/lot12/2d6ba1702416.html"),
    "xtx_markets": Path("data/discovery/lot12/058eb18a512b.html"),
}
SAMPLE_IDS = {
    8104832,
    7822791,
    6172858,
    7767735,
    8105914,
    6190021,
    7156979,
    7847009,
    8027860,
    7831489003,
    7741365003,
    7835362003,
}


def write_report(name: str, value: object) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def local_audit() -> None:
    config = load_config()
    reports = []
    for source, path in BOARDS.items():
        content = path.read_bytes()
        payload = json.loads(content)
        selected = parse_board(
            payload,
            source,
            config.companies[source],
            GreenhouseOptions.model_validate(config.companies[source].options),
        )
        scored = {raw.external_id: score_job(normalize(raw), config.keywords) for raw in selected}
        sample = []
        for row in payload["jobs"]:
            if row["id"] not in SAMPLE_IDS:
                continue
            job = scored.get(str(row["id"]))
            sample.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "url": row["absolute_url"],
                    "location": row["location"],
                    "departments": row["departments"],
                    "metadata": row["metadata"],
                    "description": plain_text(row["content"]),
                    "selected_by_current_collector": job is not None,
                    "current_score": job.score_breakdown.model_dump() if job else None,
                    "current_total": job.score_breakdown.total if job else None,
                }
            )
        reports.append(
            {
                "source": source,
                "artifact": str(path),
                "artifact_sha256": hashlib.sha256(content).hexdigest(),
                "catalogue_count": len(payload["jobs"]),
                "selected_count": len(selected),
                "sample": sample,
            }
        )
    write_report(
        "local-analysis.json",
        {
            "analyzed_at": utcnow().isoformat(),
            "live_status_verified": False,
            "scope": "Saved lot 12 catalogues; selected IDs, not exhaustive opportunity review",
            "boards": reports,
        },
    )
    print("Local catalogue analysis saved.", flush=True)


async def network_audit() -> None:
    config = load_config()
    http = HTTPClient(timeout=20, retries=0)
    events = []

    async def record(response: httpx.Response) -> None:
        # Do not persist cookies, request headers, tokens or response bodies.
        events.append(
            {
                "at": utcnow().isoformat(),
                "url": str(response.request.url),
                "status": response.status_code,
            }
        )

    http.client.event_hooks["response"].append(record)
    reports = []
    try:
        for source in ["citadel_securities", "jpmorgan"]:
            company = config.companies[source]
            start = len(events)
            report = {
                "source": source,
                "url": company.career_url,
                "checked_at": utcnow().isoformat(),
            }
            try:
                async with asyncio.timeout(60):
                    body = await http.get_text(company.career_url, 2, source)
                report.update(
                    status="accessible",
                    body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                    body_characters=len(body),
                )
            except (SourceUnavailable, TimeoutError) as exc:
                report.update(status="unavailable", reason=str(exc) or type(exc).__name__)
            report.update(request_count=http.counts[source], responses=events[start:])
            reports.append(report)
            print(source, report["status"], report.get("reason", ""), flush=True)
    finally:
        await http.close()
    write_report("access-probe.json", reports)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", action="store_true", help="Probe two configured public URLs")
    args = parser.parse_args()
    local_audit()
    if args.network:
        asyncio.run(network_audit())
