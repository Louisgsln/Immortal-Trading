"""Bounded public-source evidence; no repository, notifier, service or state writes.

Run through the validated container's Python stdin. This script inspects only
IMC, CA CIB, HSBC programmes and SIG, using their current collectors and pacing.
"""

import ast
import asyncio
import importlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from trading_radar import ca_cib, greenhouse_filtered, hsbc, sig
from trading_radar.collectors import build_collector
from trading_radar.config import load_config
from trading_radar.html_page import Document, clean, with_class
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.selection import rejection_reason
from trading_radar.source_failure import failure_summary

SOURCES = {
    "imc": (greenhouse_filtered, "parse_board"),
    "credit_agricole_cib": (ca_cib, "parse_detail"),
    "hsbc_graduates": (hsbc, "parse_detail"),
    "sig": (sig, "parse_page"),
}
HOSTS = {
    "boards-api.greenhouse.io",
    "jobs.ca-cib.com",
    "www.hsbc.com",
    "apply.careers.hsbc.com",
    "careers.sig.com",
}


def bounded(value):
    if value is None or type(value) in (bool, int, float):
        return value
    if not isinstance(value, str):
        return {"type": type(value).__name__}
    text = " ".join(value.split())
    text = re.sub(r"https?://\S+|\b[^\s@]+@[^\s@]+\b|\b\d{6,}:[\w-]{20,}\b", "[masque]", text)
    return text[:160]


def public_checks(module) -> set[str]:
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    return {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SourceUnavailable"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
        and len(node.args[0].value) <= 140
        and not re.search(r"https?://|[\r\n]", node.args[0].value)
    }


def evidence(source, args, error) -> list[dict]:
    if source == "credit_agricole_cib" and str(error) == "invalid CA CIB employment start date":
        text, row = args[:2]
        return [
            {
                "reference": bounded(row.get("reference")),
                "tag": node.tag,
                "value": bounded(clean(node)),
                "without_headings": bounded(node.text(without_headings=True)),
            }
            for node in Document(text).root.walk()
            if node.attrs.get("id") == "fldjobdescription_date1"
        ][:5]
    if source == "hsbc_graduates" and str(error) == "HSBC incomplete address":
        text, row = args[:2]
        roots = with_class(Document(text).root.walk(), "jobDisplayShell")
        result = []
        for root in roots[:1]:
            for address in (n for n in root.walk() if n.attrs.get("itemprop") == "address"):
                fields = []
                for node in address.walk():
                    if node.attrs.get("itemprop") in {
                        "addressLocality",
                        "addressRegion",
                        "addressCountry",
                    }:
                        fields.append(
                            {
                                "property": node.attrs["itemprop"],
                                "tag": node.tag,
                                "value": bounded(node.attrs.get("content") or clean(node)),
                                "nested_names": [
                                    bounded(n.attrs.get("content") or clean(n))
                                    for n in node.walk()
                                    if n.attrs.get("itemprop") == "name"
                                ][:3],
                            }
                        )
                result.append({"id": bounded(row.get("id")), "fields": fields[:8]})
        return result[:10]
    if source == "imc" and str(error) == "IMC worker level missing or unknown":
        payload, _, company, options = args[:4]
        result = []
        for row in payload.get("jobs", []):
            if not isinstance(row, dict) or row.get("internal_job_id") is None:
                continue
            if not isinstance(row.get("title"), str) or rejection_reason(row["title"], options):
                continue
            try:
                fields = greenhouse_filtered.metadata(row)
            except SourceUnavailable:
                continue
            if fields.get("Is Hidden Job?") is True:
                continue
            value = fields.get("Worker Sub Type")
            if isinstance(value, str) and value in {
                "Graduate",
                "Experienced",
                "Intern",
                "Working Student",
                "Temporary",
            }:
                continue
            result.append(
                {
                    "id": bounded(row.get("id")),
                    "field_present": "Worker Sub Type" in fields,
                    "worker_sub_type": bounded(value),
                    "field_names": [bounded(k) for k in fields][:20],
                }
            )
        return result[:15]
    return []


class ProbeHTTP(HTTPClient):
    async def _request(self, url, interval, source, *, method="GET", **kwargs):
        parts = urlsplit(url)
        if (
            method != "GET"
            or parts.scheme != "https"
            or parts.hostname not in HOSTS
            or parts.username is not None
            or parts.password is not None
            or re.search(r"/(?:login|account|talentcommunity)(?:/|$)", parts.path, re.I)
        ):
            raise SourceUnavailable("Diagnostic public scope rejected")
        if self.counts[source] >= 40:
            raise SourceUnavailable("Diagnostic request budget reached")
        return await super()._request(url, max(3, interval), source, method=method, **kwargs)


async def probe(source, config, http):
    module, name = SOURCES[source]
    original = getattr(module, name)
    report = {"source": source, "status": "unchecked", "samples": [], "pages": []}
    checks = public_checks(module) | public_checks(importlib.import_module("trading_radar.http"))

    def inspect(*args, **kwargs):
        if source == "sig":
            payload, number = args[:2]
            if isinstance(payload, dict):
                wrappers = payload.get("jobs")
                identifiers = (
                    [
                        item["data"].get("req_id")
                        for item in wrappers
                        if isinstance(item, dict) and isinstance(item.get("data"), dict)
                    ]
                    if isinstance(wrappers, list)
                    else []
                )
                report["pages"].append(
                    {
                        "page": number,
                        "totalCount": bounded(payload.get("totalCount")),
                        "count": bounded(payload.get("count")),
                        "rows": len(wrappers) if isinstance(wrappers, list) else None,
                        "first_ids": [bounded(v) for v in identifiers[:3]],
                        "last_ids": [bounded(v) for v in identifiers[-3:]],
                    }
                )
        try:
            return original(*args, **kwargs)
        except SourceUnavailable as error:
            report["samples"] = evidence(source, args, error)
            raise

    setattr(module, name, inspect)
    try:
        async with asyncio.timeout(120):
            collection = await build_collector(source, config.companies[source], http).collect()
        report.update(status="collected", jobs=len(collection.jobs))
    except SourceUnavailable as error:
        raw = str(error)
        match = re.search(r"\bHTTP\s+(\d{3})\b", raw, re.I)
        if raw in {"Diagnostic request budget reached", "Diagnostic public scope rejected"}:
            report.update(
                status="diagnostic_limit", limit="requests" if "budget" in raw else "public_scope"
            )
        else:
            report.update(
                status="failed",
                failure=failure_summary(raw),
                validation_check=raw if raw in checks else None,
                http_status=int(match[1]) if match else None,
            )
    except TimeoutError:
        report.update(status="diagnostic_timeout")
    except Exception as error:
        report.update(status="diagnostic_error", error_type=type(error).__name__)
    finally:
        setattr(module, name, original)
    report["requests"] = http.counts[source]
    return report


async def main():
    config = load_config()
    print("PROBE_LECTURE_SEULE=true", flush=True)
    for source in SOURCES:
        if source not in config.companies or not config.companies[source].enabled:
            continue
        print("PROBE_EN_COURS=" + source, flush=True)
        http = ProbeHTTP(timeout=min(config.settings.timeout, 15), retries=0)
        try:
            report = await probe(source, config, http)
            print(
                "CHAMPS_SOURCE=" + json.dumps(report, ensure_ascii=False, sort_keys=True),
                flush=True,
            )
        finally:
            await http.close()


if __name__ == "__main__":
    asyncio.run(main())
