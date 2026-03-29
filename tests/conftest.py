from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure():
    root = Path(__file__).resolve().parents[1]
    src_path = root / "src"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
