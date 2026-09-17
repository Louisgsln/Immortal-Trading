"""Read-only preview of the Optiver adapter, without database writes or notifications."""

import asyncio
from pathlib import Path

from trading_radar.collectors import build_collector
from trading_radar.config import load_config
from trading_radar.http import HTTPClient
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job


async def main():
    config = load_config()
    http = HTTPClient(retries=1)
    try:
        collection = await build_collector("optiver", config.companies["optiver"], http).collect()
        path = Path("data/discovery/lot9/optiver-preview.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(collection.model_dump_json(indent=2), encoding="utf-8")
        print(f"{len(collection.jobs)} jobs, {collection.requests} requests", flush=True)
        for raw in collection.jobs:
            job = score_job(normalize(raw), config.keywords)
            print(
                job.score_breakdown.total,
                raw.external_id,
                raw.title,
                raw.location,
                job.score_breakdown.exclusions,
                flush=True,
            )
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
