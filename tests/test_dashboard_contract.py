import json

import pytest

from trading_radar.dashboard import render_dashboard
from trading_radar.dashboard_contract import DashboardContractError, _Document, validate_dashboard


def snapshot(jobs=None):
    return {"format_version": 1, "status": "ok", "jobs": jobs or []}


def test_packaged_dashboard_contract_accepts_unicode_and_untrusted_offer_text():
    data = snapshot([{"id": "job-1", "title": "</script><img src=x> Électricité & crédit"}])
    result = validate_dashboard(render_dashboard(data, editable=True))
    assert result["jobs"] == 1
    assert result["controls"] > 40
    assert result["modules"] == 7
    assert "title" not in json.dumps(result)


def test_stale_response_security_policy_is_rejected():
    with pytest.raises(DashboardContractError, match="response_policy_mismatch"):
        validate_dashboard(render_dashboard(snapshot()), response_policy="default-src 'none'")


def test_response_can_add_the_servers_frame_protection_without_changing_asset_rules():
    html = render_dashboard(snapshot(), editable=True)
    policy = _Document(html).policy
    assert policy is not None
    assert (
        validate_dashboard(html, response_policy=policy + "; frame-ancestors 'none'")["status"]
        == "ok"
    )
    with pytest.raises(DashboardContractError, match="response_policy_mismatch"):
        validate_dashboard(html, response_policy=policy + "; script-src-elem 'unsafe-inline'")


@pytest.mark.parametrize(
    ("before", "after", "code"),
    [
        ('id="service-details"', 'id="removed-control"', "missing_control"),
        ('id="service-details"', 'id="metrics"', "duplicate_id"),
        ("<style>", "<style>/* changed */", "asset_hash_mismatch"),
        ("<script>", '<script src="https://example.com/remote.js">', "external_asset"),
    ],
)
def test_contract_blocks_incomplete_or_altered_release(before, after, code):
    html = render_dashboard(snapshot()).replace(before, after)
    with pytest.raises(DashboardContractError, match=code):
        validate_dashboard(html)


@pytest.mark.parametrize(
    "jobs", [[{"id": "same"}, {"id": "same"}], [{"id": "../private"}], [{}], [None]]
)
def test_duplicate_or_invalid_offer_ids_are_rejected(jobs):
    with pytest.raises(DashboardContractError, match="invalid_"):
        validate_dashboard(render_dashboard(snapshot(jobs)))
