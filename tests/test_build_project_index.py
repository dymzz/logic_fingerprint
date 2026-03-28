from __future__ import annotations

import importlib.util
import sqlite3
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


def test_build_index_creates_sqlite_tables(tmp_path):
    indexer = load_indexer_module()
    root = tmp_path / "sample_project"
    source_dir = root / "src" / "sample_pkg"
    tests_dir = root / "tests"
    ignored_dir = root / ".venv"
    static_dir = root / "static"
    source_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
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
    (ignored_dir / "ignored.py").write_text("raise RuntimeError('skip')\n", encoding="utf-8")
    (static_dir / "vendor.js").write_text("console.log('vendor');\n", encoding="utf-8")

    db_path = root / "analysis" / "project_index.sqlite"
    summary = indexer.build_index(root, db_path)

    assert summary["file_count"] == 5
    assert summary["python_file_count"] == 3
    assert db_path.exists()

    connection = sqlite3.connect(db_path)
    files = {
        row[0]
        for row in connection.execute("SELECT relative_path FROM files")
    }
    assert ".venv/ignored.py" not in files
    assert "static/vendor.js" not in files
    assert "src/sample_pkg/module.py" in files

    module_row = connection.execute(
        """
        SELECT module_name, class_count, function_count
        FROM python_modules
        WHERE module_name = 'sample_pkg.module'
        """
    ).fetchone()
    assert module_row == ("sample_pkg.module", 1, 1)

    symbol_names = {
        row[0]
        for row in connection.execute(
            "SELECT qualname FROM symbols WHERE file_id IN (SELECT id FROM files WHERE relative_path = 'src/sample_pkg/module.py')"
        )
    }
    assert "Demo" in symbol_names
    assert "Demo.greet" in symbol_names
    assert "add" in symbol_names

    imports = {
        row[0]
        for row in connection.execute(
            "SELECT module FROM imports WHERE file_id IN (SELECT id FROM files WHERE relative_path = 'src/sample_pkg/module.py')"
        )
    }
    assert "json" in imports

    meta = dict(connection.execute("SELECT key, value FROM project_meta"))
    assert meta["file_count"] == "5"
    connection.close()
