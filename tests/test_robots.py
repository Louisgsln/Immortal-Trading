from pathlib import Path

import pytest
from protego import Protego

from trading_radar.robots import RobotsPolicy

AGENT = "TradingJobRadar"


@pytest.mark.parametrize(
    "path,allowed",
    [
        ("/emploi-carriere/toutes-offres-emploi", True),
        ("/emploi-carriere/toutes-offres-emploi?form%5Bq%5D=trading&page=1", True),
        ("/emploi-carriere/offre-emploi/trader", True),
        ("/emploi-carriere/toutes-offres-emploi?", False),
        ("/emploi-carriere/toutes-offres-emploi?q=trading", False),
        ("/offre?ref=abc", False),
        ("/offre?campaign=abc", False),
        ("/offre?study=abc", False),
        ("/js/unavailable-offer.min.js", False),
        ("/offre/link%20", False),
    ],
)
def test_captured_bnp_policy(path, allowed):
    # Public robots.txt captured 2026-09-24, no credentials or session data.
    content = Path("tests/fixtures/bnp-robots.txt").read_text(encoding="utf-8")
    policy = RobotsPolicy.parse(content)
    assert policy.can_fetch("https://group.bnpparibas" + path, AGENT) is allowed


@pytest.mark.parametrize(
    "path,allowed",
    [
        ("/careers?", False),
        ("/careers?#fragment", False),
        ("/careers#?", True),
        ("/careers%3F", True),
    ],
)
def test_literal_query_delimiter(path, allowed):
    policy = RobotsPolicy.parse("User-agent: *\nDisallow: *?$")
    assert policy.can_fetch("https://example.com" + path, AGENT) is allowed


def test_ordinary_rules_remain_equivalent_and_specific_group_wins():
    content = (
        "User-agent: *\nDisallow: *?$\n"
        "User-agent: TradingJobRadar\nDisallow: /private\nAllow: /private/public\n"
        "Crawl-delay: 4\n"
    )
    policy = RobotsPolicy.parse(content)
    original = Protego.parse(content)
    for path in ["/", "/careers?", "/private", "/private/public", "/private/public?x=1"]:
        url = "https://example.com" + path
        assert policy.can_fetch(url, AGENT) == original.can_fetch(url, AGENT)
    assert policy.crawl_delay(AGENT) == 4
    assert not policy.can_fetch("https://example.com/careers?", "AnotherBot")
