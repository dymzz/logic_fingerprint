from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path


def _force_remove_readonly(func, path, _exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def _robust_basetemp_cleanup(basetemp: Path) -> None:
    if basetemp.exists():
        try:
            shutil.rmtree(basetemp, onexc=_force_remove_readonly)
        except Exception:
            try:
                shutil.rmtree(basetemp, ignore_errors=True)
            except Exception:
                pass
    basetemp.mkdir(parents=True, exist_ok=True)


def pytest_configure():
    root = Path(__file__).resolve().parents[1]
    src_path = root / "src"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    basetemp = root / ".pytest_tmp" / "basetemp"
    _robust_basetemp_cleanup(basetemp)
