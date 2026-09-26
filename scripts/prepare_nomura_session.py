"""Open a dedicated public Nomura browser. CAPTCHA validation is strictly manual.

Optional dependency: pip install 'trading-job-radar[browser]'.
The browser closes after a validated board; only its Nomura cookies are saved.
Never use an existing personal browser profile or an applicant account here.
"""

import argparse
import asyncio
import time
from pathlib import Path
from urllib.parse import urlsplit

from filelock import FileLock, Timeout

from trading_radar.html_page import Document
from trading_radar.http import SourceUnavailable
from trading_radar.models import utcnow
from trading_radar.nomura import SEARCH, parse_board
from trading_radar.nomura_session import HOST, save_session


async def prepare(destination: Path, *, channel: str = "msedge", timeout: int = 300) -> int:
    from playwright.async_api import async_playwright

    async with async_playwright() as driver:
        browser = await driver.chromium.launch(channel=channel, headless=False)
        try:
            context = await browser.new_context(accept_downloads=False)
            page = await context.new_page()
            await page.goto(SEARCH, wait_until="domcontentloaded", timeout=60_000)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if page.is_closed():
                    raise SourceUnavailable("Nomura browser closed; no session saved")
                # Never click/submit a CAPTCHA, login, application, or consent.
                if urlsplit(page.url).hostname != HOST:
                    raise SourceUnavailable("Nomura browser left the public host; no session saved")
                text = await page.content()
                try:
                    rows = parse_board(text, 1000)
                except SourceUnavailable:
                    await asyncio.sleep(2)
                    continue
                # A logged-in applicant context is outside this helper's scope.
                links = [
                    n.attrs.get("href", "") for n in Document(text).root.walk() if n.tag == "a"
                ]
                if not any(urlsplit(link).path.endswith("/candidate/login") for link in links):
                    raise SourceUnavailable("Nomura public login link missing; no session saved")
                cookies = [
                    {key: cookie[key] for key in ("name", "value", "domain", "path", "expires")}
                    for cookie in await context.cookies([SEARCH])
                    if cookie["domain"] in {HOST, "." + HOST}
                ]
                save_session(
                    destination,
                    {
                        "version": 1,
                        "verified_at": utcnow().isoformat(),
                        "user_agent": await page.evaluate("navigator.userAgent"),
                        "cookies": cookies,
                    },
                )
                return len(rows)
            raise SourceUnavailable("Nomura manual verification timed out; no session saved")
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Valider manuellement l'accès Nomura du radar.")
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--channel", choices=["msedge", "chrome", "chromium"], default="msedge")
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(destination) + ".lock", timeout=0):
            print(
                "Validez le CAPTCHA dans la fenêtre Nomura. Ne vous connectez pas à un compte candidat.",
                flush=True,
            )
            count = asyncio.run(prepare(destination, channel=args.channel))
            print(
                f"Accès navigateur validé : {count} offres. Session enregistrée localement.",
                flush=True,
            )
    except (Timeout, SourceUnavailable, ImportError):
        print(
            "Session non enregistrée. Vérifiez le navigateur et la dépendance optionnelle browser.",
            flush=True,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
