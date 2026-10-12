import re
from pathlib import Path

import pytest


def matcher():
    template = Path("deploy/dashboard-editor.Caddyfile.template").read_text()
    pattern = next(
        line.strip().split(" ", 2)[2]
        for line in template.splitlines()
        if "path_regexp applications " in line
    )
    return re.compile(pattern.replace("__DASHBOARD_LINK_TOKEN__", "A" * 43))


@pytest.mark.parametrize(
    "path",
    [
        "applications",
        "applications/job-id",
        "applications/job-id/applied",
        "wishlist",
        "wishlist/job-id",
    ],
)
def test_gateway_routes_only_supported_tracking_paths(path):
    assert matcher().fullmatch("/" + "A" * 43 + "/api/" + path)


@pytest.mark.parametrize(
    "path",
    [
        "/api/wishlist",
        "/" + "B" * 43 + "/api/wishlist",
        "/api/wishlist/../applications",
        "/api/applications/job/applied/extra",
        "/api/wishlist/job/extra",
        "/api/health-snapshots",
        "/api/applications/applied/extra",
        "/jobs.db",
    ],
)
def test_gateway_does_not_expand_access_to_other_resources(path):
    assert matcher().fullmatch(path) is None
    if path != "/api/wishlist":
        assert matcher().fullmatch("/" + "A" * 43 + path) is None
