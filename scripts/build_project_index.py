from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DEFAULT_EXCLUDED_DIRS = {
    "analysis",
    ".git",
    ".hg",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "static",
    "venv",
}

LANGUAGE_BY_SUFFIX = {
    ".css": "css",
    ".csv": "csv",
    ".html": "html",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "javascript",
    ".lock": "lockfile",
    ".md": "markdown",
    ".png": "png",
    ".py": "python",
    ".sh": "shell",
    ".svg": "svg",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".txt": "text",
    ".whl": "wheel",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}


@dataclass(slots=True)
class TextFileInfo:
    sha256: str
    is_binary: bool
    encoding: str | None
    line_count: int | None
    text: str | None


@dataclass(slots=True)
class ImportInfo:
    lineno: int
    module: str
    name: str | None
    alias: str | None
    is_from_import: int
    is_relative: int


@dataclass(slots=True)
class SymbolInfo:
    symbol_type: str
    name: str
    qualname: str
    lineno: int
    end_lineno: int | None
    signature: str | None
    docstring: str | None


@dataclass(slots=True)
class PythonModuleInfo:
    module_name: str
    docstring: str | None
    class_count: int
    function_count: int
    import_count: int
    parse_error: str | None
    imports: list[ImportInfo]
    symbols: list[SymbolInfo]


class PythonAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scope: list[tuple[str, str]] = []
        self.imports: list[ImportInfo] = []
        self.symbols: list[SymbolInfo] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    lineno=node.lineno,
                    module=alias.name,
                    name=None,
                    alias=alias.asname,
                    is_from_import=0,
                    is_relative=0,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module_name = "." * node.level + (node.module or "")
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    lineno=node.lineno,
                    module=module_name,
                    name=alias.name,
                    alias=alias.asname,
                    is_from_import=1,
                    is_relative=1 if node.level else 0,
                )
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualname = ".".join([*self._scope_names(), node.name])
        self.symbols.append(
            SymbolInfo(
                symbol_type="class",
                name=node.name,
                qualname=qualname,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno),
                signature=None,
                docstring=ast.get_docstring(node),
            )
        )
        self.scope.append((node.name, "class"))
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node, async_prefix=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node, async_prefix=True)

    def _record_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        async_prefix: bool,
    ) -> None:
        symbol_type = self._function_symbol_type(async_prefix=async_prefix)
        qualname = ".".join([*self._scope_names(), node.name])
        signature = build_signature(node)
        self.symbols.append(
            SymbolInfo(
                symbol_type=symbol_type,
                name=node.name,
                qualname=qualname,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno),
                signature=signature,
                docstring=ast.get_docstring(node),
            )
        )
        self.scope.append((node.name, "function"))
        self.generic_visit(node)
        self.scope.pop()

    def _function_symbol_type(self, *, async_prefix: bool) -> str:
        prefix = "async_" if async_prefix else ""
        if self.scope and self.scope[-1][1] == "class":
            return f"{prefix}method"
        if self.scope:
            return f"{prefix}nested_function"
        return f"{prefix}function"

    def _scope_names(self) -> list[str]:
        return [name for name, _ in self.scope]


def build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    parts: list[str] = []
    posonly = [arg.arg for arg in node.args.posonlyargs]
    regular = [arg.arg for arg in node.args.args]
    kwonly = [arg.arg for arg in node.args.kwonlyargs]

    if posonly:
        parts.extend(posonly)
        parts.append("/")
    parts.extend(regular)

    if node.args.vararg:
        parts.append(f"*{node.args.vararg.arg}")
    elif kwonly:
        parts.append("*")

    parts.extend(kwonly)

    if node.args.kwarg:
        parts.append(f"**{node.args.kwarg.arg}")

    return f"{node.name}({', '.join(parts)})"


def iter_project_files(root: Path, excluded_dirs: set[str]) -> Iterable[Path]:
    for current_dir, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            [
                dirname
                for dirname in dirnames
                if dirname not in excluded_dirs
                and not dirname.endswith(".egg-info")
                and not dirname.startswith(".coverage")
            ]
        )

        current_path = Path(current_dir)
        for filename in sorted(filenames):
            path = current_path / filename
            yield path


def read_text_file(path: Path) -> TextFileInfo:
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()

    if b"\x00" in raw:
        return TextFileInfo(
            sha256=sha256,
            is_binary=True,
            encoding=None,
            line_count=None,
            text=None,
        )

    for encoding in ("utf-8-sig", "utf-8"):
        try:
            text = raw.decode(encoding)
            return TextFileInfo(
                sha256=sha256,
                is_binary=False,
                encoding=encoding,
                line_count=count_lines(text),
                text=text,
            )
        except UnicodeDecodeError:
            continue

    return TextFileInfo(
        sha256=sha256,
        is_binary=True,
        encoding=None,
        line_count=None,
        text=None,
    )


def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + 1


def detect_language(path: Path) -> str:
    if path.name == ".gitignore":
        return "gitignore"
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "unknown")


def classify_file(relative_path: Path) -> str:
    name = relative_path.name.lower()
    parts = relative_path.parts
    top_level = parts[0] if len(parts) > 1 else "(root)"

    if name == "readme.md":
        return "documentation"
    if name in {"pyproject.toml", "requirements.txt", ".gitignore", "uv.lock"}:
        return "configuration"
    if top_level == "src":
        return "source"
    if top_level == "tests":
        return "test"
    if top_level == "demo":
        return "demo"
    if top_level == "design":
        return "design"
    if top_level == "static":
        return "static"
    return "project-file"


def module_name_from_path(relative_path: Path) -> str:
    parts = list(relative_path.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)


def analyze_python_source(relative_path: Path, text: str) -> PythonModuleInfo:
    module_name = module_name_from_path(relative_path)
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return PythonModuleInfo(
            module_name=module_name,
            docstring=None,
            class_count=0,
            function_count=0,
            import_count=0,
            parse_error=f"{exc.msg} (line {exc.lineno})",
            imports=[],
            symbols=[],
        )

    analyzer = PythonAnalyzer()
    analyzer.visit(tree)
    class_count = sum(isinstance(node, ast.ClassDef) for node in tree.body)
    function_count = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in tree.body
    )
    return PythonModuleInfo(
        module_name=module_name,
        docstring=ast.get_docstring(tree),
        class_count=class_count,
        function_count=function_count,
        import_count=len(analyzer.imports),
        parse_error=None,
        imports=analyzer.imports,
        symbols=analyzer.symbols,
    )


def build_summary(
    relative_path: Path,
    *,
    category: str,
    language: str,
    python_info: PythonModuleInfo | None,
    is_binary: bool,
) -> str:
    name = relative_path.name.lower()

    if is_binary:
        return "Binary asset."
    if name == "readme.md":
        return "Project overview, installation notes, and demo usage."
    if name == "pyproject.toml":
        return "Python package metadata and build configuration."
    if name == "requirements.txt":
        return "Pinned runtime dependencies."
    if name == "uv.lock":
        return "Resolved dependency lockfile."
    if name == ".gitignore":
        return "Repository ignore rules."
    if category == "test":
        target = relative_path.stem.removeprefix("test_")
        return f"Pytest coverage for {target or relative_path.stem}."
    if category == "demo":
        return "Runnable example that demonstrates the safety layer."
    if category == "design":
        return "Design or planning artifact."
    if category == "static":
        if language in {"javascript", "typescript", "css", "html"}:
            return "Vendored frontend asset or source file."
        return "Static project asset."
    if python_info:
        if python_info.docstring:
            return python_info.docstring.splitlines()[0].strip()
        names = [symbol.name for symbol in python_info.symbols if "." not in symbol.qualname]
        if names:
            label = "module symbols" if len(names) > 1 else "module symbol"
            return f"Python source file containing {label}: {', '.join(names[:6])}."
        return "Python source file."
    if language == "markdown":
        return "Markdown document."
    if language == "toml":
        return "TOML configuration file."
    if language == "json":
        return "JSON data or configuration file."
    return "Project file."


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE project_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE top_level_stats (
            top_level TEXT PRIMARY KEY,
            file_count INTEGER NOT NULL,
            text_file_count INTEGER NOT NULL,
            python_file_count INTEGER NOT NULL,
            total_bytes INTEGER NOT NULL
        );

        CREATE TABLE files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relative_path TEXT NOT NULL UNIQUE,
            absolute_path TEXT NOT NULL,
            top_level TEXT NOT NULL,
            parent_dir TEXT NOT NULL,
            file_name TEXT NOT NULL,
            extension TEXT NOT NULL,
            language TEXT NOT NULL,
            category TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            line_count INTEGER,
            modified_at TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            is_binary INTEGER NOT NULL,
            encoding TEXT,
            summary TEXT
        );

        CREATE TABLE python_modules (
            file_id INTEGER PRIMARY KEY,
            module_name TEXT NOT NULL,
            docstring TEXT,
            class_count INTEGER NOT NULL,
            function_count INTEGER NOT NULL,
            import_count INTEGER NOT NULL,
            parse_error TEXT,
            FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE TABLE symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            symbol_type TEXT NOT NULL,
            name TEXT NOT NULL,
            qualname TEXT NOT NULL,
            lineno INTEGER NOT NULL,
            end_lineno INTEGER,
            signature TEXT,
            docstring TEXT,
            FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE TABLE imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            lineno INTEGER NOT NULL,
            module TEXT NOT NULL,
            name TEXT,
            alias TEXT,
            is_from_import INTEGER NOT NULL,
            is_relative INTEGER NOT NULL,
            FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
        );

        CREATE INDEX idx_files_top_level ON files(top_level);
        CREATE INDEX idx_files_language ON files(language);
        CREATE INDEX idx_files_category ON files(category);
        CREATE INDEX idx_symbols_name ON symbols(name);
        CREATE INDEX idx_symbols_qualname ON symbols(qualname);
        CREATE INDEX idx_imports_module ON imports(module);

        CREATE VIEW python_file_overview AS
        SELECT
            files.relative_path,
            files.summary,
            python_modules.module_name,
            python_modules.class_count,
            python_modules.function_count,
            python_modules.import_count,
            python_modules.parse_error
        FROM files
        JOIN python_modules ON python_modules.file_id = files.id;
        """
    )


def insert_meta(connection: sqlite3.Connection, metadata: dict[str, str]) -> None:
    connection.executemany(
        "INSERT INTO project_meta (key, value) VALUES (?, ?)",
        sorted(metadata.items()),
    )


def build_index(
    root: Path,
    db_path: Path,
    *,
    excluded_dirs: set[str] | None = None,
) -> dict[str, int]:
    if excluded_dirs is None:
        excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    create_schema(connection)
    db_artifact_paths = {
        db_path.resolve(),
        Path(f"{db_path.resolve()}-journal"),
        Path(f"{db_path.resolve()}-shm"),
        Path(f"{db_path.resolve()}-wal"),
    }

    top_level_stats: dict[str, Counter[str]] = defaultdict(Counter)
    category_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()

    indexed_files = 0
    indexed_python_files = 0
    indexed_symbols = 0
    indexed_imports = 0
    total_bytes = 0

    with connection:
        for path in iter_project_files(root, excluded_dirs):
            if path.resolve() in db_artifact_paths:
                continue
            relative_path = path.relative_to(root)
            posix_relative_path = relative_path.as_posix()
            top_level = relative_path.parts[0] if len(relative_path.parts) > 1 else "(root)"
            parent_dir = (
                relative_path.parent.as_posix()
                if str(relative_path.parent) != "."
                else ""
            )
            category = classify_file(relative_path)
            language = detect_language(relative_path)
            file_info = read_text_file(path)
            modified_at = datetime.fromtimestamp(
                path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()
            python_info = None
            if language == "python" and file_info.text is not None:
                python_info = analyze_python_source(relative_path, file_info.text)

            summary = build_summary(
                relative_path,
                category=category,
                language=language,
                python_info=python_info,
                is_binary=file_info.is_binary,
            )

            cursor = connection.execute(
                """
                INSERT INTO files (
                    relative_path,
                    absolute_path,
                    top_level,
                    parent_dir,
                    file_name,
                    extension,
                    language,
                    category,
                    size_bytes,
                    line_count,
                    modified_at,
                    sha256,
                    is_binary,
                    encoding,
                    summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    posix_relative_path,
                    str(path.resolve()),
                    top_level,
                    parent_dir,
                    relative_path.name,
                    path.suffix.lower(),
                    language,
                    category,
                    path.stat().st_size,
                    file_info.line_count,
                    modified_at,
                    file_info.sha256,
                    int(file_info.is_binary),
                    file_info.encoding,
                    summary,
                ),
            )
            file_id = cursor.lastrowid
            indexed_files += 1
            total_bytes += path.stat().st_size
            category_counts[category] += 1
            language_counts[language] += 1
            top_level_stats[top_level]["file_count"] += 1
            top_level_stats[top_level]["total_bytes"] += path.stat().st_size

            if not file_info.is_binary:
                top_level_stats[top_level]["text_file_count"] += 1

            if python_info:
                connection.execute(
                    """
                    INSERT INTO python_modules (
                        file_id,
                        module_name,
                        docstring,
                        class_count,
                        function_count,
                        import_count,
                        parse_error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        python_info.module_name,
                        python_info.docstring,
                        python_info.class_count,
                        python_info.function_count,
                        python_info.import_count,
                        python_info.parse_error,
                    ),
                )
                indexed_python_files += 1
                top_level_stats[top_level]["python_file_count"] += 1

                for symbol in python_info.symbols:
                    connection.execute(
                        """
                        INSERT INTO symbols (
                            file_id,
                            symbol_type,
                            name,
                            qualname,
                            lineno,
                            end_lineno,
                            signature,
                            docstring
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            file_id,
                            symbol.symbol_type,
                            symbol.name,
                            symbol.qualname,
                            symbol.lineno,
                            symbol.end_lineno,
                            symbol.signature,
                            symbol.docstring,
                        ),
                    )
                    indexed_symbols += 1

                for imported in python_info.imports:
                    connection.execute(
                        """
                        INSERT INTO imports (
                            file_id,
                            lineno,
                            module,
                            name,
                            alias,
                            is_from_import,
                            is_relative
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            file_id,
                            imported.lineno,
                            imported.module,
                            imported.name,
                            imported.alias,
                            imported.is_from_import,
                            imported.is_relative,
                        ),
                    )
                    indexed_imports += 1

        connection.executemany(
            """
            INSERT INTO top_level_stats (
                top_level,
                file_count,
                text_file_count,
                python_file_count,
                total_bytes
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    top_level,
                    stats["file_count"],
                    stats["text_file_count"],
                    stats["python_file_count"],
                    stats["total_bytes"],
                )
                for top_level, stats in sorted(top_level_stats.items())
            ],
        )

        insert_meta(
            connection,
            {
                "root_path": str(root.resolve()),
                "database_path": str(db_path.resolve()),
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "excluded_directories": json.dumps(sorted(excluded_dirs), ensure_ascii=True),
                "file_count": str(indexed_files),
                "python_file_count": str(indexed_python_files),
                "symbol_count": str(indexed_symbols),
                "import_count": str(indexed_imports),
                "total_bytes": str(total_bytes),
                "category_counts": json.dumps(category_counts, ensure_ascii=True, sort_keys=True),
                "language_counts": json.dumps(language_counts, ensure_ascii=True, sort_keys=True),
            },
        )

    connection.close()
    return {
        "file_count": indexed_files,
        "python_file_count": indexed_python_files,
        "symbol_count": indexed_symbols,
        "import_count": indexed_imports,
        "total_bytes": total_bytes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a project tree and store a file index in SQLite.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root to scan. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("analysis") / "project_index.sqlite",
        help="SQLite database output path.",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Extra directory names to exclude. Can be passed multiple times.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    db_path = args.db if args.db.is_absolute() else (root / args.db)
    excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)
    excluded_dirs.update(args.exclude_dir)
    summary = build_index(root, db_path, excluded_dirs=excluded_dirs)
    print(
        json.dumps(
            {
                "root": str(root),
                "db_path": str(db_path.resolve()),
                **summary,
            },
            ensure_ascii=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
