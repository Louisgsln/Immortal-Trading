import asyncio
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts.prepare_nomura_session import prepare
from tests.test_nomura import board, card
from tests.test_nomura_session import state
from trading_radar.http import SourceUnavailable
from trading_radar.nomura import SEARCH
from trading_radar.nomura_session import load_session


@pytest.mark.parametrize("case", ["success", "captcha", "offsite", "account", "closed", "timeout"])
def test_manual_browser_only_saves_verified_public_board(tmp_path, monkeypatch, case):
    text = board([card()]) + '<a href="https://nomuracampus.tal.net/candidate/login">Login</a>'
    if case == "account":
        text = board([card()])
    page = SimpleNamespace(
        goto=AsyncMock(),
        content=AsyncMock(
            side_effect=['<form id="captcha-form"></form>', text] if case == "captcha" else [text]
        ),
        evaluate=AsyncMock(return_value="TestPublicBrowser/1.0"),
        url="https://evil.example/" if case == "offsite" else SEARCH,
        is_closed=lambda: case == "closed",
    )
    context = SimpleNamespace(
        new_page=AsyncMock(return_value=page), cookies=AsyncMock(return_value=state()["cookies"])
    )
    browser = SimpleNamespace(new_context=AsyncMock(return_value=context), close=AsyncMock())
    launch = AsyncMock(return_value=browser)

    class Driver:
        async def __aenter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(launch=launch))

        async def __aexit__(self, *args):
            pass

    # Unit tests need no browser or optional Playwright installation.
    api = ModuleType("playwright.async_api")
    api.async_playwright = Driver
    monkeypatch.setitem(sys.modules, "playwright", ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.async_api", api)
    monkeypatch.setattr("scripts.prepare_nomura_session.asyncio.sleep", AsyncMock())
    path = tmp_path / "session.json"
    if case in {"success", "captcha"}:
        assert asyncio.run(prepare(path)) == 1
        assert load_session(path).headers(SEARCH)["Cookie"] == "public_session=fixture-only"
    else:
        with pytest.raises(SourceUnavailable):
            asyncio.run(prepare(path, timeout=0 if case == "timeout" else 300))
        assert not path.exists()
    launch.assert_awaited_once_with(channel="msedge", headless=False)
    browser.close.assert_awaited_once()
    page.goto.assert_awaited_once_with(SEARCH, wait_until="domcontentloaded", timeout=60_000)
