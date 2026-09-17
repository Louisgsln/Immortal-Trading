"""Optional third-party boundary; no import-time optional dependencies."""

import contextlib
import json
import math
import sys

from trading_radar.deadlines import aware_instant
from trading_radar.models import Collection, RawJob
from trading_radar.normalizer import parse_date


def clean(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


def map_row(row: dict, source: str, ats: bool) -> RawJob:
    row = {key: clean(value) for key, value in row.items()}
    return RawJob(
        company=row.get("company") or "Unknown",
        title=row["title"],
        apply_url=str(
            row.get("apply_url")
            or row.get("job_url_direct")
            or row.get("job_url")
            or row.get("url")
            or ""
        ),
        external_id=str(row.get("ats_id") or row.get("id") or "") or None,
        source=source,
        source_type="aggregator",
        description=row.get("description") or "",
        location=row.get("location") or "",
        source_url=str(row.get("url") or row.get("job_url") or ""),
        date_posted=parse_date(row.get("posted_at") if ats else row.get("date_posted")),
        application_deadline=aware_instant(row.get("application_deadline")),
    )


def collect(kind: str, options: dict, source: str) -> Collection:
    if kind == "ats_dataset":
        from ats_scrapers import search

        allowed = {"query", "location", "ats", "limit"}
        if set(options) - allowed:
            raise ValueError("unsupported ATS dataset options")
        if not options.get("ats"):
            raise ValueError("choose a per-ATS dataset to bound download size")
        frame = search(**options)
    elif kind == "jobspy":
        from jobspy import scrape_jobs

        allowed = {
            "site_name",
            "search_term",
            "location",
            "country_indeed",
            "results_wanted",
            "hours_old",
        }
        if set(options) - allowed:
            raise ValueError("unsupported JobSpy options")
        sites = options.get("site_name", ["indeed"])
        if (
            not isinstance(sites, list)
            or not sites
            or set(sites) - {"indeed", "google", "glassdoor", "zip_recruiter"}
        ):
            raise ValueError("only public supported job boards are allowed; LinkedIn is disabled")
        if not 1 <= int(options.get("results_wanted", 50)) <= 500:
            raise ValueError("results_wanted must be between 1 and 500")
        frame = scrape_jobs(**{**options, "site_name": sites, "verbose": 0})
    else:
        raise ValueError("unknown optional collector")
    return Collection(
        jobs=[
            map_row(row, source, kind == "ats_dataset") for row in frame.to_dict(orient="records")
        ],
        complete=False,
    )


def main() -> None:
    request = json.load(sys.stdin)
    with contextlib.redirect_stdout(sys.stderr):
        result = collect(**request)
    sys.stdout.write(result.model_dump_json())


if __name__ == "__main__":
    main()
