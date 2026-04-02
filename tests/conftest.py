from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest


def pytest_configure(config):
    root = Path(__file__).resolve().parents[1]
    src_path = root / "src"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parents[1] / ".tmp" / "pytest-fixtures"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"pytest-{os.getpid()}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path
