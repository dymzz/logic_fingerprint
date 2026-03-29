from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_indexer_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_project_index.py"
    spec = importlib.util.spec_from_file_location("build_project_index", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_index_creates_json_index(tmp_path, monkeypatch):
    indexer = load_indexer_module()
    root = tmp_path / "sample_project"
    source_dir = root / "src" / "sample_pkg"
    tests_dir = root / "tests"
    demo_dir = root / "demo"
    ignored_dir = root / ".venv"
    static_dir = root / "static"
    source_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    demo_dir.mkdir(parents=True)
    ignored_dir.mkdir(parents=True)
    static_dir.mkdir(parents=True)

    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (source_dir / "__init__.py").write_text("", encoding="utf-8")
    (source_dir / "module.py").write_text(
        "import json\n\n"
        "class Demo:\n"
        "    def greet(self, name):\n"
        "        return f'hello {name}'\n\n"
        "def add(x, y):\n"
        "    return x + y\n",
        encoding="utf-8",
    )
    (tests_dir / "test_module.py").write_text("def test_add():\n    assert True\n", encoding="utf-8")
    (demo_dir / "example.py").write_text("print('demo')\n", encoding="utf-8")
    (ignored_dir / "ignored.py").write_text("raise RuntimeError('skip')\n", encoding="utf-8")
    (static_dir / "vendor.js").write_text("console.log('vendor');\n", encoding="utf-8")

    monkeypatch.setattr(
        indexer,
        "run_rg_files",
        lambda root, *, excluded_dirs=None, rg_executable=None: [
            "README.md",
            "pyproject.toml",
            "src/sample_pkg/__init__.py",
            "src/sample_pkg/module.py",
            "tests/test_module.py",
            "demo/example.py",
            ".venv/ignored.py",
            "static/vendor.js",
        ],
    )
    monkeypatch.setattr(indexer, "resolve_rg_executable", lambda: Path("rg"))

    index_path = root / "analysis" / "project_index.json"
    summary = indexer.build_index(root, index_path)

    assert summary["file_count"] == 5
    assert summary["python_file_count"] == 3
    assert index_path.exists()

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    files = {row["relative_path"] for row in payload["files"]}
    assert ".venv/ignored.py" not in files
    assert "demo/example.py" not in files
    assert "static/vendor.js" not in files
    assert "src/sample_pkg/module.py" in files

    module_rows = {
        row["module_name"]: row
        for row in payload["python_modules"]
    }
    assert module_rows["sample_pkg.module"]["class_count"] == 1
    assert module_rows["sample_pkg.module"]["function_count"] == 1

    module_file_id = next(
        item["id"]
        for item in payload["files"]
        if item["relative_path"] == "src/sample_pkg/module.py"
    )
    symbol_names = {
        row["qualname"]
        for row in payload["symbols"]
        if row["file_id"] == module_file_id
    }
    assert "Demo" in symbol_names
    assert "Demo.greet" in symbol_names
    assert "add" in symbol_names

    imports = {
        row["module"]
        for row in payload["imports"]
        if row["file_id"] == module_file_id
    }
    assert "json" in imports

    metadata = payload["metadata"]
    assert metadata["file_count"] == 5
    assert "demo" in metadata["excluded_directories"]
