import importlib
import sys

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("fastapi")

sys.modules.pop("logicfp", None)
logicfp = importlib.import_module("logicfp")
engineering = importlib.import_module("logicfp.engineering")

from logicfp import create_protector, protect
from logicfp.engineering import (
    assemble_runtime,
    build_demo_runtime,
    build_production_runtime,
    build_runtime,
    create_app,
    create_demo_app,
)


def test_root_package_exports_user_mode_only():
    assert logicfp.__all__ == ["protect", "create_protector"]
    assert callable(protect)
    assert callable(create_protector)


def test_root_package_guides_engineering_imports():
    with pytest.raises(AttributeError, match="logicfp.engineering"):
        logicfp.build_production_runtime


def test_engineering_module_exports_service_entrypoints():
    assert engineering.__all__ == [
        "assemble_runtime",
        "build_demo_runtime",
        "build_production_runtime",
        "build_runtime",
        "create_app",
        "create_demo_app",
    ]
    assert callable(assemble_runtime)
    assert callable(build_demo_runtime)
    assert callable(build_production_runtime)
    assert callable(build_runtime)
    assert callable(create_app)
    assert callable(create_demo_app)
