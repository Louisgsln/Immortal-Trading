"""Re-read three real Goldman roles; verify idempotence in a disposable DB backup."""

import asyncio
import json
import sqlite3
import tempfile
from pathlib import Path

from trading_radar.config import load_config
from trading_radar.goldman import GoldmanCollector
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection
from trading_radar.scanner import scan
from trading_radar.storage import Repository


async def main():
    config = load_config()
    config.settings.alerts_enabled = False
    source_path = Path(config.settings.database_url.removeprefix("sqlite:///"))
    parent = Path("data/validation")
    parent.mkdir(parents=True, exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix="goldman-", dir=parent)) / "repeat.db"
    with sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True) as original:
        with sqlite3.connect(target) as copied:
            original.backup(copied)
    config.settings.database_url = "sqlite:///" + target.as_posix()
    repo = Repository(config.settings.database_url)
    http = HTTPClient(retries=1)
    try:
        jobs = [job for job in repo.list_jobs() if job.source == "goldman_sachs"][:3]
        if len(jobs) != 3:
            raise ValueError("Import Goldman first")
        before = {job.id: job.first_seen for job in jobs}
        adapter = GoldmanCollector("goldman_sachs", config.companies["goldman_sachs"], http)

        class Subset:
            async def collect(self):
                found = []
                for job in jobs:
                    detail = await adapter._detail(str(job.external_id), {})
                    if detail is None:
                        raise SourceUnavailable("Selected validation role became inactive")
                    found.append(detail)
                return Collection(jobs=found, complete=False, requests=http.counts["goldman_sachs"])

        metrics = await scan(config, repo, collectors={"goldman_sachs": Subset()}, http=http)
        if metrics.failed or metrics.new or metrics.updated or metrics.closed or metrics.alerts:
            raise ValueError(f"Repeat requires review: {metrics.model_dump_json()}")
        assert all(repo.get(key).first_seen == value for key, value in before.items())
        print(
            json.dumps(
                {
                    "database_copy": str(target),
                    "first_seen_preserved": True,
                    "metrics": metrics.model_dump(),
                },
                indent=2,
            )
        )
    finally:
        repo.close()
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())
