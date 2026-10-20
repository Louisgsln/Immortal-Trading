"""Synthetic private gateway contract, executed inside the offline smoke container."""

import json
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.managed_runtime import gateway_config
from trading_radar.config import Config, Settings
from trading_radar.dashboard_editor import create_editable_dashboard_server
from trading_radar.dashboard_private import PrivateDashboardAccess
from trading_radar.storage import Repository


def main() -> None:
    access = PrivateDashboardAccess(
        "https://synthetic.onrender.com", "/" + "p" * 43 + "/", "s" * 43
    )
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        url = f"sqlite:///{root / 'jobs.db'}"
        Repository(url).close()
        config = Config(settings=Settings(database_url=url), companies={}, keywords={})
        server = create_editable_dashboard_server(config, root / "history", private_access=access)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        caddyfile = root / "Caddyfile"
        caddyfile.write_text(gateway_config("active", 10001, access))
        child = subprocess.Popen(
            ["caddy", "run", "--config", str(caddyfile), "--adapter", "caddyfile"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            page = None
            for _ in range(20):
                try:
                    page = urlopen("http://127.0.0.1:10001" + access.prefix, timeout=5)
                    break
                except OSError:
                    time.sleep(0.25)
            assert page is not None, "Private gateway did not start"
            with page:
                payload = re.search(
                    r'<script id="radar-data" type="application/json">(.*?)</script>',
                    page.read().decode(),
                    re.S,
                )
                assert payload
                data = json.loads(payload[1])
                assert (
                    data["status"] == "ok"
                    and data["editing"]["mode"] == "private"
                    and data["live"] is True
                )
                cookie = page.headers["Set-Cookie"].split(";", 1)[0]
                assert "Secure; HttpOnly; SameSite=Strict" in page.headers["Set-Cookie"]
            path = "http://127.0.0.1:10001" + access.prefix + "api/wishlist"
            headers = {
                "Cookie": cookie,
                "X-Radar-Token": data["editing"]["token"],
                "Origin": access.origin,
            }
            with urlopen(Request(path, headers=headers), timeout=5) as response:
                assert response.status == 200
            for wrong in (
                {"Origin": "https://attacker.example"},
                {"X-Radar-Token": "invalid"},
                {"Cookie": "invalid"},
            ):
                try:
                    urlopen(Request(path, headers={**headers, **wrong}), timeout=5)
                    raise AssertionError("Private API accepted invalid browser credentials")
                except HTTPError as error:
                    assert error.code == 403
            try:
                urlopen("http://127.0.0.1:10001/", timeout=5)
                raise AssertionError("Root exposed private Dashboard")
            except HTTPError as error:
                assert error.code == 404
            print(
                json.dumps(
                    {
                        "gateway_private": True,
                        "sites_snapshot_compatible": True,
                        "origin_session_csrf": True,
                    }
                )
            )
        finally:
            child.terminate()
            child.wait(timeout=10)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
