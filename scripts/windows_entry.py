"""Load the installed service package without the Windows venv redirector process."""

import runpy
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
packages = root / "data/service-venv/Lib/site-packages"
if sys.platform != "win32" or not packages.is_dir():
    raise SystemExit("Installed Windows service environment required")
sys.path.insert(0, str(packages))
runpy.run_path(str(root / "scripts/windows_service.py"), run_name="__main__")
