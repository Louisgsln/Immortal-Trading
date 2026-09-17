"""Compare bounded public Workday searches; no database writes or notifications."""

import asyncio
import json
from pathlib import Path

from trading_radar.config import load_config
from trading_radar.http import HTTPClient, SourceUnavailable
from trading_radar.models import utcnow
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.workday import WorkdayCollector

TERMS = ["trading", "trader", "structuring", "repo", "securities finance"]


async def main():
    config = load_config()
    root = Path("data/discovery/lot15")
    root.mkdir(parents=True, exist_ok=True)
    http = HTTPClient(retries=1)
    semaphore = asyncio.Semaphore(4)

    async def audit(source, company):
        report = {"source": source, "checked_at": utcnow().isoformat(), "queries": []}
        async with semaphore:
            collector = WorkdayCollector(source, company, http)
            selected, baseline = {}, set()
            try:
                async with asyncio.timeout(600):
                    for term in TERMS:
                        rows = await collector._search(term)
                        targets = {p: r for p, r in rows.items() if collector.selected(r["title"])}
                        if term == "trading":
                            baseline = set(targets)
                        extra = set(targets) - baseline
                        report["queries"].append(
                            {
                                "term": term,
                                "raw": len(rows),
                                "selected": len(targets),
                                "outside_trading": len(extra),
                                "new_to_union": len(set(targets) - set(selected)),
                            }
                        )
                        for path, row in targets.items():
                            if path in selected and selected[path]["title"] != row["title"]:
                                raise SourceUnavailable("Conflicting titles across audit queries")
                            selected[path] = row
                        print(source, report["queries"][-1], flush=True)
                    extras = {p: r for p, r in selected.items() if p not in baseline}
                    if len(extras) > collector.options.max_details:
                        raise SourceUnavailable("Audit detail limit exceeded")
                    jobs = [await collector._detail(p, r) for p, r in extras.items()]
                    (root / f"{source}-extra-jobs.json").write_text(
                        json.dumps([j.model_dump(mode="json") for j in jobs], indent=2),
                        encoding="utf-8",
                    )
                    report["extra_jobs"] = []
                    for raw in jobs:
                        job = score_job(normalize(raw), config.keywords)
                        report["extra_jobs"].append(
                            {
                                "id": raw.external_id,
                                "title": raw.title,
                                "url": raw.apply_url,
                                "score": job.score_breakdown.total,
                                "exclusions": job.score_breakdown.exclusions,
                            }
                        )
                    report["status"] = "ok"
                    report["union_selected"] = len(selected)
            except (SourceUnavailable, TimeoutError) as exc:
                report["status"] = "failed"
                report["error"] = str(exc) or type(exc).__name__
            report["requests"] = http.counts[source]
            (root / f"{source}-audit.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            print(
                source,
                report["status"],
                report.get("union_selected"),
                report["requests"],
                flush=True,
            )
            return report

    try:
        reports = await asyncio.gather(
            *(audit(s, c) for s, c in config.companies.items() if c.enabled and c.ats == "workday")
        )
    finally:
        await http.close()
    (root / "workday-audit.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
