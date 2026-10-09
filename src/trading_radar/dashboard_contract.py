"""Validate the installed Dashboard document before switching release images."""

import base64
import hashlib
import json
import re
from html.parser import HTMLParser


class DashboardContractError(ValueError):
    """Public error codes only; never include embedded tracking or access values."""


class _Document(HTMLParser):
    def __init__(self, html: str):
        super().__init__()
        self.ids: set[str] = set()
        self.policy: str | None = None
        self.scripts: list[dict] = []
        self.styles: list[dict] = []
        self.block: dict | None = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            if values["id"] in self.ids:
                raise DashboardContractError("duplicate_id")
            self.ids.add(values["id"])
        if tag == "meta" and values.get("http-equiv", "").lower() == "content-security-policy":
            if self.policy is not None:
                raise DashboardContractError("duplicate_policy")
            self.policy = values.get("content", "")
        if (tag == "script" and "src" in values) or (
            tag == "link" and values.get("rel", "").lower() == "stylesheet"
        ):
            raise DashboardContractError("external_asset")
        if tag in {"script", "style"}:
            self.block = {"attrs": values, "text": ""}
            (self.scripts if tag == "script" else self.styles).append(self.block)

    def handle_data(self, data):
        if self.block is not None:
            self.block["text"] += data

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.block = None


def validate_dashboard(html: str, *, response_policy: str | None = None) -> dict:
    """Check asset hashes, literal DOM references and bounded, unique offer identifiers."""
    if not isinstance(html, str) or len(html) > 64 * 1024 * 1024:
        raise DashboardContractError("invalid_document")
    document = _Document(html)
    if response_policy is not None:

        def directives(policy: str) -> set[str]:
            return {" ".join(part.split()) for part in policy.split(";") if part.strip()}

        required = directives(document.policy or "")
        received = directives(response_policy)
        # frame-ancestors is enforced in the HTTP header, never in a meta policy.
        if not required <= received or received - required - {"frame-ancestors 'none'"}:
            raise DashboardContractError("response_policy_mismatch")
    data_blocks = [b for b in document.scripts if b["attrs"].get("id") == "radar-data"]
    scripts = [b for b in document.scripts if b["attrs"].get("id") != "radar-data"]
    if (
        len(data_blocks) != 1
        or data_blocks[0]["attrs"].get("type") != "application/json"
        or len(scripts) != 1
        or len(document.styles) != 1
        or document.policy is None
    ):
        raise DashboardContractError("invalid_assets")
    script = scripts[0]["text"]
    references = set(re.findall(r"\$\([\"']([\w-]+)[\"']\)", script))
    if references - document.ids:
        raise DashboardContractError("missing_control")
    for source, directive in [(script, "script-src"), (document.styles[0]["text"], "style-src")]:
        digest = base64.b64encode(hashlib.sha256(source.encode()).digest()).decode()
        expected = directive + " 'sha256-" + digest + "'"
        if expected not in document.policy.split("; "):
            raise DashboardContractError("asset_hash_mismatch")
    modules = (
        "radarTime",
        "radarProgramme",
        "radarOpportunity",
        "radarAgenda",
        "radarTracking",
        "radarPreferences",
        "radarCalendar",
    )
    if any("const " + name + " =" not in script for name in modules):
        raise DashboardContractError("missing_module")
    try:
        data = json.loads(data_blocks[0]["text"])
        if not isinstance(data, dict) or data.get("format_version") != 1:
            raise DashboardContractError("invalid_snapshot")
        jobs = data.get("jobs")
        if data.get("status") != "ok" or not isinstance(jobs, list) or len(jobs) > 5000:
            raise DashboardContractError("invalid_snapshot")
        ids = [job["id"] for job in jobs]
        if any(
            not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is None
            for value in ids
        ) or len(set(ids)) != len(ids):
            raise DashboardContractError("invalid_job_ids")
    except (KeyError, TypeError, ValueError, RecursionError) as error:
        if isinstance(error, DashboardContractError):
            raise
        raise DashboardContractError("invalid_snapshot") from None
    return {
        "status": "ok",
        "jobs": len(jobs),
        "controls": len(references),
        "modules": len(modules),
        "asset_hashes": "verified",
    }


def main() -> None:
    from trading_radar.dashboard import render_dashboard

    # The release image checks its packaged assets without business data or network access.
    snapshot = {"format_version": 1, "status": "ok", "jobs": []}
    print(json.dumps(validate_dashboard(render_dashboard(snapshot, editable=True)), sort_keys=True))


if __name__ == "__main__":
    main()
