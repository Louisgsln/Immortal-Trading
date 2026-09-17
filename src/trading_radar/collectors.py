"""Collectors only retrieve public postings. They never submit applications."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode

from trading_radar.config import Company
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import parse_date


class Collector(Protocol):
    async def collect(self) -> Collection: ...


class FixtureCollector:
    def __init__(self, path: Path, source: str = "demo"):
        self.path, self.source = path, source

    async def collect(self) -> Collection:
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        return Collection(
            jobs=[
                RawJob(**{**row, "source": self.source, "source_type": "fixture"}) for row in rows
            ],
            complete=True,
        )


class PublicATSCollector:
    def __init__(self, source: str, config: Company, http: HTTPClient):
        if not config.tenant:
            raise ValueError("ATS tenant is required")
        self.source, self.config, self.http = source, config, http

    async def fetch(self, url: str):
        return await self.http.get_json(url, self.config.request_interval, self.source)

    def raw(self, row: dict, **fields) -> RawJob:
        return RawJob(
            company=self.config.name,
            source=self.source,
            source_type="official",
            source_url=self.config.career_url,
            raw_payload=row,
            **fields,
        )

    async def collect(self) -> Collection:
        ats, tenant = self.config.ats, self.config.tenant
        before = self.http.counts[self.source]
        jobs: list[RawJob] = []
        if ats == "greenhouse":
            payload = await self.fetch(
                f"https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs?content=true"
            )
            rows = payload["jobs"]
            if not isinstance(rows, list):
                raise SourceUnavailable("invalid Greenhouse jobs list")
            for row in rows:
                jobs.append(
                    self.raw(
                        row,
                        external_id=str(row["id"]),
                        title=row["title"],
                        apply_url=row["absolute_url"],
                        location=(row.get("location") or {}).get("name", ""),
                        description=row.get("content", ""),
                    )
                )
                # updated_at is NOT a publication date.
        elif ats == "lever":
            skip = 0
            while True:
                region = (
                    "api.eu.lever.co" if self.config.country.upper() == "EU" else "api.lever.co"
                )
                rows = await self.fetch(
                    f"https://{region}/v0/postings/{tenant}?"
                    + urlencode({"mode": "json", "skip": skip, "limit": 100})
                )
                if not isinstance(rows, list):
                    raise SourceUnavailable("invalid Lever postings list")
                for row in rows:
                    description = (
                        row.get("descriptionPlain", "")
                        + " "
                        + " ".join(item.get("content", "") for item in row.get("lists", []))
                    )
                    jobs.append(
                        self.raw(
                            row,
                            external_id=str(row["id"]),
                            title=row["text"],
                            apply_url=row.get("applyUrl") or row["hostedUrl"],
                            location=(row.get("categories") or {}).get("location", ""),
                            description=description,
                            employment_type=(row.get("categories") or {}).get("commitment"),
                        )
                    )
                if len(rows) < 100:
                    break
                skip += 100
                if skip >= 10000:
                    raise SourceUnavailable("pagination safety limit reached; incomplete snapshot")
        elif ats == "ashby":
            payload = await self.fetch(f"https://api.ashbyhq.com/posting-api/job-board/{tenant}")
            rows = payload["jobs"]
            if not isinstance(rows, list):
                raise SourceUnavailable("invalid Ashby jobs list")
            for row in rows:
                if row.get("isListed") is False:
                    continue
                jobs.append(
                    self.raw(
                        row,
                        external_id=row.get("id") or row["jobUrl"],
                        title=row["title"],
                        apply_url=row["applyUrl"],
                        location=row.get("location", ""),
                        description=row.get("descriptionPlain", ""),
                        date_posted=parse_date(row.get("publishedAt")),
                        remote=row.get("isRemote"),
                        employment_type=row.get("employmentType"),
                    )
                )
        else:
            raise SourceUnavailable(f"direct ATS not implemented: {ats}")
        return Collection(jobs=jobs, complete=True, requests=self.http.counts[self.source] - before)


class VendorCollector:
    """Run optional libraries in killable child processes with explicit input/output boundaries."""

    def __init__(self, source: str, config: Company):
        self.source, self.config = source, config

    async def collect(self) -> Collection:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "trading_radar.vendor",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            output, _ = await asyncio.wait_for(
                process.communicate(
                    json.dumps(
                        {
                            "kind": self.config.ats,
                            "options": self.config.options,
                            "source": self.source,
                        }
                    ).encode()
                ),
                timeout=90,
            )
        except (TimeoutError, asyncio.CancelledError):
            process.kill()
            await process.wait()
            raise SourceUnavailable("optional collector timed out or cancelled") from None
        if process.returncode:
            raise SourceUnavailable(
                "optional collector failed; check dependency and configuration with doctor"
            )
        return Collection.model_validate_json(output)


def build_collector(source: str, config: Company, http: HTTPClient) -> Collector:
    if config.ats == "nomura_professionals":
        from trading_radar.nomura_professionals import NomuraProfessionalsCollector

        return NomuraProfessionalsCollector(source, config, http)
    if config.ats == "hsbc_professionals":
        from trading_radar.hsbc_professionals import HSBCProfessionalsCollector

        return HSBCProfessionalsCollector(source, config, http)
    if config.ats == "sig":
        from trading_radar.sig import SIGCollector

        return SIGCollector(source, config, http)
    if config.ats == "greenhouse_filtered":
        from trading_radar.greenhouse_filtered import GreenhouseFilteredCollector

        return GreenhouseFilteredCollector(source, config, http)
    if config.ats == "optiver":
        from trading_radar.optiver import OptiverCollector

        return OptiverCollector(source, config, http)
    if config.ats == "macquarie":
        from trading_radar.macquarie import MacquarieCollector

        return MacquarieCollector(source, config, http)
    if config.ats == "nomura":
        from trading_radar.nomura import NomuraCollector

        return NomuraCollector(source, config, http)
    if config.ats == "ca_cib":
        from trading_radar.ca_cib import CACIBCollector

        return CACIBCollector(source, config, http)
    if config.ats == "hsbc":
        from trading_radar.hsbc import HSBCCollector

        return HSBCCollector(source, config, http)
    if config.ats == "societe_generale":
        from trading_radar.societe_generale import SocieteGeneraleCollector

        return SocieteGeneraleCollector(source, config, http)
    if config.ats == "ubs":
        from trading_radar.ubs import UBSCollector

        return UBSCollector(source, config, http)
    if config.ats == "bnp":
        from trading_radar.bnp import BNPCollector

        return BNPCollector(source, config, http)
    if config.ats == "goldman":
        from trading_radar.goldman import GoldmanCollector

        return GoldmanCollector(source, config, http)
    if config.ats == "oracle":
        from trading_radar.oracle import OracleCollector

        return OracleCollector(source, config, http)
    if config.ats == "workday":
        from trading_radar.workday import WorkdayCollector

        return WorkdayCollector(source, config, http)
    if config.ats in {"greenhouse", "lever", "ashby"}:
        return PublicATSCollector(source, config, http)
    if config.ats in {"ats_dataset", "jobspy"}:
        return VendorCollector(source, config)
    raise SourceUnavailable(f"collector not implemented: {config.ats}")
