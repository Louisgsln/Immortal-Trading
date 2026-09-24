import asyncio
import csv
import json

import httpx

from trading_radar.export import export_csv, safe_cell
from trading_radar.notifications import TelegramNotifier


def test_telegram_mock(job):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    notifier = TelegramNotifier("123:test_token", "456", transport=httpx.MockTransport(handler))
    asyncio.run(notifier.send(job, "new"))
    assert requests[0]["chat_id"] == "456"
    assert "100/100" in requests[0]["text"]
    assert requests[0]["parse_mode"] == "HTML"
    assert requests[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == job.apply_url


def test_csv(repo, job, tmp_path):
    with repo.transaction():
        repo.upsert(job)
    path = tmp_path / "jobs.csv"
    assert export_csv(repo, path) == 1
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["score"] == "100"
    assert rows[0]["status"] == "New"
    assert safe_cell("=HYPERLINK('bad')").startswith("'")
