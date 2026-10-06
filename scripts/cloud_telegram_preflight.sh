#!/usr/bin/env bash
# Read-only cloud diagnostics; never activate flags or send Telegram messages.
(
set -euo pipefail
cd "${RADAR_PROJECT_DIR:-$HOME/Immortal-Trading}"
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml ps
radar_lanceurs_ok="$(sudo python3 - <<'PY'
import json
import re
import runpy
import subprocess
import sys
inventory = runpy.run_path('src/trading_radar/launchers.py')['launcher_report']()
workers = [p for p in inventory['processes'] if p['kind'] == 'worker']
counts = {mode: sum(p['mode'] == mode for p in workers) for mode in ('watch', 'telegram')}
print('LANCEURS_CONNUS=' + json.dumps({'status': inventory['status'], 'counts': counts, 'issues': inventory['issues']}, sort_keys=True), file=sys.stderr)
logs = subprocess.run(['docker', 'compose', '--env-file', '.env.cloud', '-f', 'compose.cloud.yaml', 'logs', '--no-color', '--no-log-prefix', '--since', '2h', '--tail', '1500', 'radar'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True)
explain = runpy.run_path('src/trading_radar/source_failure.py')['failure_summary']
latest = {}
for line in (logs.stdout + '\n' + logs.stderr).splitlines():
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if isinstance(event, dict) and event.get('event') == 'source_failed':
        raw = event.get('error')
        match = re.search(r'\bHTTP\s+(\d{3})\b', raw, re.I) if isinstance(raw, str) else None
        latest[str(event.get('source'))] = {'at': event.get('timestamp'), 'failure': explain(raw), 'http_status': int(match[1]) if match else None}
print('ECHECS_RECENTS=' + json.dumps(latest, ensure_ascii=False, sort_keys=True), file=sys.stderr)
print('true' if inventory['status'] == 'ok' and counts == {'watch': 1, 'telegram': 0} and not inventory['issues'] else 'false')
PY
)"
sudo docker compose --env-file .env.cloud -f compose.cloud.yaml exec -T -e "RADAR_LANCEURS_OK=$radar_lanceurs_ok" radar python - <<'PY'
import asyncio
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from trading_radar.backups import database_path
from trading_radar.config import load_config
from trading_radar.health import check_health
from trading_radar.http import SourceUnavailable
from trading_radar.nomura_session import load_session, session_path
from trading_radar.notifications import TelegramNotifier
from trading_radar.runtime_status import watcher_status
from trading_radar.telegram_control import ControlState, api

def emit(name, value):
    print(name + '=' + json.dumps(value, ensure_ascii=False, sort_keys=True), flush=True)

config = load_config()
health = check_health(config)
emit('SOURCES_A_VERIFIER', [{k: s[k] for k in ('source', 'company', 'status', 'age_hours', 'last_success', 'last_failure', 'consecutive_failures', 'failure', 'schedule')} for s in health['sources'] if s['status'] != 'fresh'])
nomura_path = session_path()
nomura_ok = False
if nomura_path is not None:
    try:
        load_session(nomura_path)
        nomura_ok = True
    except SourceUnavailable:
        pass
emit('NOMURA_SESSION', {'configuree': nomura_path is not None, 'locale_valide': nomura_ok})
blocked = []
if health['database']['status'] != 'ok':
    raise SystemExit('Base non valide : preparation interrompue.')
path = database_path(config.settings.database_url)
with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
    db.execute('PRAGMA query_only=ON')
    counts = dict(db.execute('SELECT status,COUNT(*) FROM alerts GROUP BY status'))
emit('ALERTES_PAR_ETAT', counts)
if any(counts.get(s, 0) for s in ('pending', 'sending', 'unknown')):
    blocked.append('alertes_a_revoir')
if watcher_status(config)['status'] != 'active':
    blocked.append('watcher_inactif')
if os.getenv('RADAR_LANCEURS_OK') != 'true':
    blocked.append('lanceurs_a_verifier')
if os.getenv('RADAR_CUTOVER_CONFIRMED') != 'true':
    blocked.append('bascule_non_confirmee')
if not config.settings.bootstrap_silent:
    blocked.append('premiere_collecte_non_silencieuse')
if config.settings.alerts_enabled or config.settings.telegram_control_enabled:
    blocked.append('envois_deja_actives')
if any(i['code'] in ('source_invalid_timestamp', 'scan_invalid_timestamp') for i in health['issues']):
    blocked.append('horloge_ou_dates_a_verifier')

try:
    notifier = TelegramNotifier.from_env()
    state_path = path.with_suffix('.telegram.json')
    state = ControlState.model_validate_json(state_path.read_text(encoding='utf-8')) if state_path.exists() else None
    expected = hashlib.sha256((notifier.token.split(':', 1)[0] + ':' + notifier.chat_id).encode()).hexdigest()
    state_ok = state is None or state.binding == expected
    emit('ETAT_TELEGRAM', {'present': state is not None, 'compatible': state_ok, 'offset': state.offset if state else None, 'digest_actif': state.digest_enabled if state else False, 'dernier_digest': state.digest_last_day if state else None})
    if not state_ok:
        blocked.append('etat_telegram_autre_destination')

    async def probe():
        return await asyncio.gather(api(notifier, 'getMe', {}), api(notifier, 'getChat', {'chat_id': notifier.chat_id}), api(notifier, 'getWebhookInfo', {}))
    me, chat, webhook = asyncio.run(probe())
    bot_ok = isinstance(me, dict) and me.get('is_bot') is True and str(me.get('id')) == notifier.token.split(':', 1)[0] and isinstance(me.get('username'), str)
    chat_ok = isinstance(chat, dict) and chat.get('type') == 'private' and type(chat.get('id')) is int and chat['id'] > 0 and str(chat['id']) == notifier.chat_id
    webhook_ok = isinstance(webhook, dict) and webhook.get('url') == ''
    pending = webhook.get('pending_update_count') if isinstance(webhook, dict) else None
    emit('API_TELEGRAM', {'bot_valide': bot_ok, 'chat_prive_valide': chat_ok, 'sans_webhook': webhook_ok, 'updates_en_attente': pending})
    if not bot_ok or not chat_ok or not webhook_ok:
        blocked.append('identite_chat_ou_webhook_a_verifier')
    if type(pending) is not int or pending < 0 or (pending and (state is None or state.offset == 0)):
        blocked.append('curseur_telegram_a_verifier')
except (ValueError, OSError, RuntimeError):
    blocked.append('etat_ou_api_telegram_indisponible')

emit('PREACTIVATION', {'prete': not blocked, 'blocages': blocked, 'envois_actifs': config.settings.alerts_enabled, 'controle_actif': config.settings.telegram_control_enabled})
raise SystemExit(1 if blocked else 0)
PY
)
