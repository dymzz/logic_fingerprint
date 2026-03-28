from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_script_module(name: str, relative_path: str):
    script_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_sample_index(tmp_path):
    indexer = load_script_module("build_project_index_for_query_test", "scripts/build_project_index.py")
    root = tmp_path / "sample_project"
    source_dir = root / "src" / "sample_pkg"
    tests_dir = root / "tests"
    source_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
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

    db_path = root / "analysis" / "project_index.sqlite"
    indexer.build_index(root, db_path)
    return db_path


def test_search_modules_and_symbols(tmp_path):
    query_module = load_script_module("query_project_index", "scripts/query_project_index.py")
    db_path = build_sample_index(tmp_path)
    connection = query_module.connect_database(db_path)
    try:
        modules = query_module.search_modules(connection, "sample_pkg.module", exact=True)
        assert len(modules) == 1
        assert modules[0]["relative_path"] == "src/sample_pkg/module.py"

        symbols = query_module.search_symbols(connection, "greet", exact=True)
        assert len(symbols) == 1
        assert symbols[0]["qualname"] == "Demo.greet"

        module_output = query_module.format_module_results(
            modules,
            connection=connection,
            with_symbols=True,
            symbol_limit=10,
        )
        assert "symbols:" in module_output
        assert "Demo.greet" in module_output

        symbol_output = query_module.format_symbol_results(symbols)
        assert "src/sample_pkg/module.py:4" in symbol_output
        assert "type: method" in symbol_output
    finally:
        connection.close()


def test_run_query_json_payload(tmp_path):
    query_module = load_script_module("query_project_index_json", "scripts/query_project_index.py")
    db_path = build_sample_index(tmp_path)
    parser = query_module.build_parser()
    args = parser.parse_args(
        [
            "--db",
            str(db_path),
            "--json",
            "module",
            "sample_pkg",
            "--with-symbols",
            "--symbol-limit",
            "5",
        ]
    )

    output, exit_code = query_module.run_query(args)

    assert exit_code == 0
    assert '"command": "module"' in output
    assert '"module_name": "sample_pkg.module"' in output
    assert '"qualname": "Demo.greet"' in output
