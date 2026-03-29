from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
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
    ".pytest_tmp",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".uv-cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "demo",
    "dist",
    "node_modules",
    "static",
    "venv",
}

DEFAULT_INDEX_PATH = Path("analysis") / "project_index.json"
LEGACY_SQLITE_SUFFIXES = {".db", ".sqlite"}
RG_ENV_VAR = "RG_PATH"
FALLBACK_RG_CANDIDATES = (
    r"D:\DevTools\Cherry Studio\resources\app.asar.unpacked\node_modules\@anthropic-ai\claude-agent-sdk\vendor\ripgrep\x64-win32\rg.exe",
    r"D:\DevTools\WeChatWebDEVTool\code\package.nw\node_modules\vscode-ripgrep\bin\rg.exe",
)

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


def iter_rg_candidates() -> Iterable[Path]:
    seen: set[str] = set()

    env_value = os.environ.get(RG_ENV_VAR)
    if env_value:
        candidate = Path(env_value)
        normalized = str(candidate)
        if normalized not in seen:
            seen.add(normalized)
            yield candidate

    result = subprocess.run(
        ["where.exe", "rg"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            candidate = Path(line.strip())
            normalized = str(candidate)
            if normalized not in seen:
                seen.add(normalized)
                yield candidate

    for raw_path in FALLBACK_RG_CANDIDATES:
        candidate = Path(raw_path)
        normalized = str(candidate)
        if normalized not in seen:
            seen.add(normalized)
            yield candidate


def resolve_rg_executable() -> Path:
    for candidate in iter_rg_candidates():
        try:
            result = subprocess.run(
                [str(candidate), "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError:
            continue
        if result.returncode == 0:
            return candidate

    raise RuntimeError(
        "Unable to locate a usable rg executable. "
        "Set RG_PATH to a working ripgrep binary."
    )


def build_rg_command(rg_executable: Path, excluded_dirs: set[str]) -> list[str]:
    command = [str(rg_executable), "--files", "-uu", "--no-messages"]
    for dirname in sorted(excluded_dirs):
        command.extend(["-g", f"!{dirname}/**"])
        command.extend(["-g", f"!**/{dirname}/**"])
    command.extend(["-g", "!pytest-cache-files-*/**"])
    command.extend(["-g", "!**/pytest-cache-files-*/**"])
    command.extend(["-g", "!*.egg-info/**"])
    command.extend(["-g", "!**/*.egg-info/**"])
    command.extend(["-g", "!.coverage*"])
    command.extend(["-g", "!**/.coverage*"])
    return command


def run_rg_files(
    root: Path,
    *,
    excluded_dirs: set[str] | None = None,
    rg_executable: Path | None = None,
) -> list[str]:
    if excluded_dirs is None:
        excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)
    if rg_executable is None:
        rg_executable = resolve_rg_executable()

    command = build_rg_command(rg_executable, excluded_dirs)
    result = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    lines = [line for line in (result.stdout or "").splitlines() if line.strip()]
    if lines:
        return lines
    if result.returncode != 0:
        stderr = (result.stderr or "").strip() or (result.stdout or "").strip()
        raise RuntimeError(f"rg file scan failed: {stderr or 'unknown error'}")
    return []


def normalize_relative_path(path_text: str) -> Path:
    return Path(path_text.replace("\\", "/"))


def should_exclude_relative_path(relative_path: Path, excluded_dirs: set[str]) -> bool:
    for part in relative_path.parts:
        if part in excluded_dirs:
            return True
        if part.startswith("pytest-cache-files-"):
            return True
        if part.endswith(".egg-info"):
            return True
        if part.startswith(".coverage"):
            return True
    return False


def iter_project_files(
    root: Path,
    excluded_dirs: set[str],
    *,
    rg_executable: Path | None = None,
) -> Iterable[Path]:
    seen: set[Path] = set()
    for path_text in sorted(
        run_rg_files(root, excluded_dirs=excluded_dirs, rg_executable=rg_executable)
    ):
        relative_path = normalize_relative_path(path_text)
        if should_exclude_relative_path(relative_path, excluded_dirs):
            continue
        path = (root / relative_path).resolve()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
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


def build_index(
    root: Path,
    index_path: Path,
    *,
    excluded_dirs: set[str] | None = None,
) -> dict[str, int]:
    if excluded_dirs is None:
        excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)
    else:
        excluded_dirs = set(excluded_dirs)

    if index_path.suffix.lower() in LEGACY_SQLITE_SUFFIXES:
        raise RuntimeError(
            "SQLite output is disabled. Use a JSON path such as analysis/project_index.json."
        )

    root = root.resolve()
    index_path = index_path if index_path.is_absolute() else (root / index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.exists():
        index_path.unlink()

    rg_executable = resolve_rg_executable()
    artifact_paths = {index_path.resolve()}

    top_level_stats: dict[str, Counter[str]] = defaultdict(Counter)
    category_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()

    file_rows: list[dict[str, object]] = []
    python_module_rows: list[dict[str, object]] = []
    symbol_rows: list[dict[str, object]] = []
    import_rows: list[dict[str, object]] = []

    indexed_files = 0
    indexed_python_files = 0
    indexed_symbols = 0
    indexed_imports = 0
    total_bytes = 0

    for file_id, path in enumerate(
        iter_project_files(root, excluded_dirs, rg_executable=rg_executable),
        start=1,
    ):
        if path.resolve() in artifact_paths:
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
        stat_result = path.stat()
        modified_at = datetime.fromtimestamp(
            stat_result.st_mtime,
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

        file_rows.append(
            {
                "id": file_id,
                "relative_path": posix_relative_path,
                "absolute_path": str(path.resolve()),
                "top_level": top_level,
                "parent_dir": parent_dir,
                "file_name": relative_path.name,
                "extension": path.suffix.lower(),
                "language": language,
                "category": category,
                "size_bytes": stat_result.st_size,
                "line_count": file_info.line_count,
                "modified_at": modified_at,
                "sha256": file_info.sha256,
                "is_binary": int(file_info.is_binary),
                "encoding": file_info.encoding,
                "summary": summary,
            }
        )

        indexed_files += 1
        total_bytes += stat_result.st_size
        category_counts[category] += 1
        language_counts[language] += 1
        top_level_stats[top_level]["file_count"] += 1
        top_level_stats[top_level]["total_bytes"] += stat_result.st_size

        if not file_info.is_binary:
            top_level_stats[top_level]["text_file_count"] += 1

        if python_info:
            python_module_rows.append(
                {
                    "file_id": file_id,
                    "module_name": python_info.module_name,
                    "docstring": python_info.docstring,
                    "class_count": python_info.class_count,
                    "function_count": python_info.function_count,
                    "import_count": python_info.import_count,
                    "parse_error": python_info.parse_error,
                }
            )
            indexed_python_files += 1
            top_level_stats[top_level]["python_file_count"] += 1

            for symbol_id, symbol in enumerate(
                python_info.symbols,
                start=indexed_symbols + 1,
            ):
                symbol_rows.append(
                    {
                        "id": symbol_id,
                        "file_id": file_id,
                        "symbol_type": symbol.symbol_type,
                        "name": symbol.name,
                        "qualname": symbol.qualname,
                        "lineno": symbol.lineno,
                        "end_lineno": symbol.end_lineno,
                        "signature": symbol.signature,
                        "docstring": symbol.docstring,
                    }
                )
            indexed_symbols += len(python_info.symbols)

            for import_id, imported in enumerate(
                python_info.imports,
                start=indexed_imports + 1,
            ):
                import_rows.append(
                    {
                        "id": import_id,
                        "file_id": file_id,
                        "lineno": imported.lineno,
                        "module": imported.module,
                        "name": imported.name,
                        "alias": imported.alias,
                        "is_from_import": imported.is_from_import,
                        "is_relative": imported.is_relative,
                    }
                )
            indexed_imports += len(python_info.imports)

    payload = {
        "format": "project-index-v2",
        "generator": "scripts/build_project_index.py",
        "backend": "rg+json",
        "metadata": {
            "root_path": str(root),
            "index_path": str(index_path.resolve()),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "rg_executable": str(rg_executable),
            "excluded_directories": sorted(excluded_dirs),
            "file_count": indexed_files,
            "python_file_count": indexed_python_files,
            "symbol_count": indexed_symbols,
            "import_count": indexed_imports,
            "total_bytes": total_bytes,
            "category_counts": dict(sorted(category_counts.items())),
            "language_counts": dict(sorted(language_counts.items())),
        },
        "top_level_stats": [
            {
                "top_level": top_level,
                "file_count": stats["file_count"],
                "text_file_count": stats["text_file_count"],
                "python_file_count": stats["python_file_count"],
                "total_bytes": stats["total_bytes"],
            }
            for top_level, stats in sorted(top_level_stats.items())
        ],
        "files": file_rows,
        "python_modules": python_module_rows,
        "symbols": symbol_rows,
        "imports": import_rows,
    }
    index_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    return {
        "file_count": indexed_files,
        "python_file_count": indexed_python_files,
        "symbol_count": indexed_symbols,
        "import_count": indexed_imports,
        "total_bytes": total_bytes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a project tree with rg and store a JSON file index.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root to scan. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_PATH,
        help="JSON index output path.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
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
    if args.db is not None:
        raise RuntimeError(
            "SQLite output is disabled. Use --index analysis/project_index.json instead."
        )

    root = args.root.resolve()
    index_path = args.index if args.index.is_absolute() else (root / args.index)
    excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)
    excluded_dirs.update(args.exclude_dir)
    summary = build_index(root, index_path, excluded_dirs=excluded_dirs)
    print(
        json.dumps(
            {
                "root": str(root),
                "index_path": str(index_path.resolve()),
                "backend": "rg+json",
                **summary,
            },
            ensure_ascii=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
