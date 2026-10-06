"""Activate an audited cloud deployment while preserving delivery and command state."""

import fcntl
import json
import os
import re
import stat
import subprocess
import tempfile
import time
from pathlib import Path

COMPOSE = ["sudo", "docker", "compose", "--env-file", ".env.cloud", "-f", "compose.cloud.yaml"]
INVENTORY = """
import json, runpy
r = runpy.run_path('src/trading_radar/launchers.py')['launcher_report']()
p = [p for p in r['processes'] if p['kind'] == 'worker']
print(json.dumps({'status': r['status'], 'issues': r['issues'],
                  'counts': {m: sum(x['mode'] == m for x in p) for m in ('watch', 'telegram')}}))
"""
FROZEN_CHECK = """
import hashlib, json, os, sqlite3
from contextlib import ExitStack, closing
from pathlib import Path
from uuid import uuid4
from filelock import FileLock
from scripts.cloud_runtime import backup_once
from trading_radar.backups import database_path
from trading_radar.config import load_config
from trading_radar.health import check_health
from trading_radar.notifications import TelegramNotifier
from trading_radar.runtime_status import pulse_path
from trading_radar.telegram_control import ControlState

c = load_config()
if (c.settings.alerts_enabled or c.settings.telegram_control_enabled or
    c.settings.telegram_incident_notices_enabled or c.settings.deadline_reminders_enabled or
    not c.settings.bootstrap_silent or os.getenv('RADAR_CUTOVER_CONFIRMED') != 'true' or
    check_health(c)['database']['status'] != 'ok'):
    raise SystemExit('Activation bloquee : configuration ou base a revoir.')
p = database_path(c.settings.database_url)
state_path = p.with_suffix('.telegram.json')
with ExitStack() as stack:
    for lock in (str(pulse_path(c)) + '.lock', str(state_path) + '.lock', str(p) + '.lock'):
        stack.enter_context(FileLock(lock, timeout=0))
    with closing(sqlite3.connect(p.as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        if db.execute("SELECT COUNT(*) FROM alerts WHERE status IN ('pending','sending','unknown')").fetchone()[0]:
            raise SystemExit('Activation bloquee : file d alertes a revoir.')
        sent = db.execute("SELECT id,event_key FROM alerts WHERE status='sent' ORDER BY id").fetchall()
    data = state_path.read_bytes() if state_path.exists() else None
    if data is not None:
        state = ControlState.model_validate_json(data)
        notifier = TelegramNotifier.from_env()
        binding = hashlib.sha256((notifier.token.split(':', 1)[0] + ':' + notifier.chat_id).encode()).hexdigest()
        if state.binding != binding:
            raise SystemExit('Activation bloquee : destination Telegram differente.')
    backup = backup_once(c)
    directory = p.parent / ('telegram-activation-' + uuid4().hex)
    directory.mkdir(mode=0o700)
    baseline = directory / 'baseline.json'
    baseline.write_text(json.dumps({'sent': sent}), encoding='utf-8')
    baseline.chmod(0o600)
    if data is not None:
        snapshot = directory / 'telegram-state.json'
        snapshot.write_bytes(data)
        snapshot.chmod(0o600)
    print(json.dumps({'snapshot': str(baseline), 'sent_preserves': len(sent), 'backup': backup}))
"""
LIVE_CHECK = """
import json, os, sqlite3
from contextlib import closing
from pathlib import Path
from trading_radar.backups import database_path
from trading_radar.config import load_config
from trading_radar.runtime_status import watcher_status

c = load_config()
if (not c.settings.alerts_enabled or not c.settings.telegram_control_enabled or
    c.settings.telegram_incident_notices_enabled or c.settings.deadline_reminders_enabled):
    raise SystemExit('Reglages actifs differents de la reprise prevue.')
baseline = json.loads(Path(os.environ['RADAR_ACTIVATION_SNAPSHOT']).read_text())
p = database_path(c.settings.database_url)
with closing(sqlite3.connect(p.as_uri() + '?mode=ro', uri=True)) as db:
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    rows = {r[0]: (r[1], r[2]) for r in db.execute('SELECT id,event_key,status FROM alerts')}
    if any(rows.get(identifier) != (key, 'sent') for identifier, key in baseline['sent']):
        raise SystemExit('Historique des envois different : verification requise.')
    counts = dict(db.execute('SELECT status,COUNT(*) FROM alerts GROUP BY status'))
print(json.dumps({'watcher': watcher_status(c)['status'], 'sent_preserves': len(baseline['sent']),
                  'alerts': True, 'controle': True, 'incidents': False, 'rappels': False,
                  'alertes_par_etat': counts}))
"""


def enabled_environment(before: bytes) -> bytes:
    """Change exactly two explicit false assignments; preserve all other bytes."""
    after = before
    for key in (b"ALERTS_ENABLED", b"TELEGRAM_CONTROL_ENABLED"):
        assignments = re.findall(rb"(?m)^\s*(?:export\s+)?" + key + rb"\s*=", after)
        pattern = rb"(?m)^(" + key + rb"=)false(?=\r?$)"
        if len(assignments) != 1:
            raise ValueError("Missing or duplicate activation flag")
        after, count = re.subn(pattern, rb"\g<1>true", after)
        if count != 1:
            raise ValueError("Expected an explicit disabled flag")
    return after


def replace_private(path: Path, content: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix=".env.cloud.write-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def compose(*args: str, code: str | None = None, capture: bool = False) -> str:
    result = subprocess.run(
        [*COMPOSE, *args], input=code, text=True, capture_output=True, check=True, timeout=120
    )
    return result.stdout if capture else ""


def inventory(expected: dict[str, int]) -> dict:
    result = subprocess.run(
        ["sudo", "python3", "-c", INVENTORY],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    report = json.loads(result.stdout)
    if report["status"] != "ok" or report["issues"] or report["counts"] != expected:
        raise ValueError("Known workers differ from expected count")
    return report


def activate(project: Path) -> int:
    os.chdir(project)
    env_path = Path(".env.cloud")
    metadata = env_path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise ValueError("Expected an owned regular environment file")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ValueError("Expected private environment permissions")
    before = env_path.read_bytes()
    after = enabled_environment(before)
    paused, changed = False, False
    with Path(".cloud-telegram-activation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            subprocess.run(
                ["bash", str(Path(__file__).with_name("cloud_telegram_preflight.sh"))],
                check=True,
                timeout=120,
            )
            saved = Path(tempfile.mkdtemp(prefix=".env.cloud.activation-", dir=project))
            replace_private(saved / "before", before)
            paused = True  # A failed stop can still have interrupted the scanner.
            compose("stop", "radar")
            inventory({"watch": 0, "telegram": 0})
            evidence = json.loads(
                compose(
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "--entrypoint",
                    "python",
                    "radar",
                    "-",
                    code=FROZEN_CHECK,
                    capture=True,
                ).splitlines()[-1]
            )
            print("SAUVEGARDE_PREACTIVATION=" + json.dumps(evidence["backup"]), flush=True)
            if env_path.read_bytes() != before:
                raise ValueError("Environment changed during activation")
            replace_private(env_path, after)
            changed = True
            compose("config", "--quiet")
            compose("up", "-d", "--no-deps", "radar")
            compose("--profile", "telegram", "up", "-d", "--no-deps", "telegram")
            for attempt in range(15):
                live = json.loads(
                    compose(
                        "exec",
                        "-T",
                        "-e",
                        "RADAR_ACTIVATION_SNAPSHOT=" + evidence["snapshot"],
                        "radar",
                        "python",
                        "-",
                        code=LIVE_CHECK,
                        capture=True,
                    )
                )
                if live["watcher"] == "active":
                    break
                if attempt == 14:
                    raise ValueError("Watcher did not resume")
                time.sleep(1)
            report = inventory({"watch": 1, "telegram": 1})
            print("LANCEURS_APRES_ACTIVATION=" + json.dumps(report), flush=True)
            print("ACTIVATION=" + json.dumps(live), flush=True)
            print("ACTIVATION_TERMINEE", flush=True)
            return 0
        except (Exception, KeyboardInterrupt) as error:
            print("ACTIVATION_INTERROMPUE=" + type(error).__name__, flush=True)
            if paused:
                try:
                    compose("--profile", "telegram", "stop", "telegram")
                    if changed:
                        if env_path.read_bytes() != after:
                            raise ValueError("Environment changed; automatic rollback refused")
                        replace_private(env_path, before)
                    elif env_path.read_bytes() != before:
                        raise ValueError("Environment changed; automatic restart refused")
                    compose("up", "-d", "--no-deps", "radar")
                    print("REPRISE_ENVOIS_DESACTIVES=true", flush=True)
                except Exception as recovery_error:
                    print("REPRISE_A_VERIFIER=" + type(recovery_error).__name__, flush=True)
            # Never restore the database or command cursor after possible sends.
            return 1


if __name__ == "__main__":
    try:
        raise SystemExit(
            activate(
                Path(
                    os.getenv("RADAR_PROJECT_DIR", str(Path.home() / "Immortal-Trading"))
                ).resolve()
            )
        )
    except (OSError, ValueError) as error:
        print("ACTIVATION_BLOQUEE=" + type(error).__name__, flush=True)
        raise SystemExit(1) from None
