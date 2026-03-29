from __future__ import annotations

import sys
import types
from pathlib import Path


def pytest_configure():
    root = Path(__file__).resolve().parents[1]
    src_path = root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Avoid executing logicfp/__init__.py (it pulls runtime deps).
    pkg_root = src_path / "logicfp"
    if "logicfp" not in sys.modules and pkg_root.exists():
        module = types.ModuleType("logicfp")
        module.__path__ = [str(pkg_root)]
        sys.modules["logicfp"] = module
