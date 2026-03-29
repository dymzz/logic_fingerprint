from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_INDEX_PATH = Path("analysis") / "project_index.json"


@dataclass(slots=True)
class LoadedIndex:
    payload: dict[str, object]
    files_by_id: dict[int, dict[str, object]]
    module_by_file_id: dict[int, dict[str, object]]
    symbols_by_file_id: dict[int, list[dict[str, object]]]


def load_index(index_path: Path) -> LoadedIndex:
    if not index_path.exists():
        raise FileNotFoundError(f"JSON index not found: {index_path}")

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    required_keys = {"files", "python_modules", "symbols", "imports", "metadata"}
    missing = required_keys - set(payload)
    if missing:
        raise RuntimeError(
            "JSON index is missing required keys: " + ", ".join(sorted(missing))
        )

    files = payload["files"]
    python_modules = payload["python_modules"]
    symbols = payload["symbols"]
    if (
        not isinstance(files, list)
        or not isinstance(python_modules, list)
        or not isinstance(symbols, list)
    ):
        raise RuntimeError("JSON index has an unexpected structure.")

    files_by_id = {int(item["id"]): item for item in files}
    module_by_file_id = {
        int(item["file_id"]): item
        for item in python_modules
    }
    symbols_by_file_id: dict[int, list[dict[str, object]]] = {}
    for symbol in symbols:
        file_id = int(symbol["file_id"])
        symbols_by_file_id.setdefault(file_id, []).append(symbol)

    return LoadedIndex(
        payload=payload,
        files_by_id=files_by_id,
        module_by_file_id=module_by_file_id,
        symbols_by_file_id=symbols_by_file_id,
    )


def connect_database(index_path: Path) -> LoadedIndex:
    return load_index(index_path)


def build_module_row(index: LoadedIndex, module: dict[str, object]) -> dict[str, object]:
    file_row = index.files_by_id[int(module["file_id"])]
    return {
        "file_id": int(module["file_id"]),
        "relative_path": file_row["relative_path"],
        "summary": file_row["summary"],
        "module_name": module["module_name"],
        "class_count": int(module["class_count"]),
        "function_count": int(module["function_count"]),
        "import_count": int(module["import_count"]),
        "parse_error": module["parse_error"],
        "file_name": file_row["file_name"],
    }


def build_symbol_row(index: LoadedIndex, symbol: dict[str, object]) -> dict[str, object]:
    file_id = int(symbol["file_id"])
    file_row = index.files_by_id[file_id]
    module = index.module_by_file_id.get(file_id)
    return {
        "id": int(symbol["id"]),
        "symbol_type": symbol["symbol_type"],
        "name": symbol["name"],
        "qualname": symbol["qualname"],
        "lineno": int(symbol["lineno"]),
        "end_lineno": symbol["end_lineno"],
        "signature": symbol["signature"],
        "docstring": symbol["docstring"],
        "file_id": file_id,
        "relative_path": file_row["relative_path"],
        "module_name": module["module_name"] if module else None,
    }


def search_modules(
    index: LoadedIndex,
    query: str,
    *,
    limit: int = 10,
    exact: bool = False,
) -> list[dict[str, object]]:
    lowered = query.lower()
    rows = [build_module_row(index, module) for module in index.payload["python_modules"]]

    if exact:
        matches = [
            row
            for row in rows
            if row["module_name"].lower() == lowered
            or row["relative_path"].lower() == lowered
        ]
        matches.sort(key=lambda item: (str(item["module_name"]), str(item["relative_path"])))
        return matches[:limit]

    def rank(row: dict[str, object]) -> tuple[object, ...]:
        module_name = str(row["module_name"]).lower()
        relative_path = str(row["relative_path"]).lower()
        file_name = str(row["file_name"]).lower()
        if lowered not in module_name and lowered not in relative_path and lowered not in file_name:
            return (99,)
        if module_name == lowered:
            bucket = 0
        elif relative_path == lowered:
            bucket = 1
        elif module_name.startswith(lowered):
            bucket = 2
        elif relative_path.startswith(lowered):
            bucket = 3
        elif file_name.startswith(lowered):
            bucket = 4
        else:
            bucket = 5
        return (
            bucket,
            -int(row["import_count"]),
            -int(row["function_count"]),
            str(row["relative_path"]),
        )

    matches = [row for row in rows if rank(row)[0] != 99]
    matches.sort(key=rank)
    return matches[:limit]


def search_symbols(
    index: LoadedIndex,
    query: str,
    *,
    limit: int = 10,
    exact: bool = False,
) -> list[dict[str, object]]:
    lowered = query.lower()
    rows = [build_symbol_row(index, symbol) for symbol in index.payload["symbols"]]

    if exact:
        matches = [
            row
            for row in rows
            if row["name"].lower() == lowered or row["qualname"].lower() == lowered
        ]
        matches.sort(
            key=lambda item: (
                str(item["qualname"]),
                str(item["relative_path"]),
                int(item["lineno"]),
            )
        )
        return matches[:limit]

    def rank(row: dict[str, object]) -> tuple[object, ...]:
        name = str(row["name"]).lower()
        qualname = str(row["qualname"]).lower()
        relative_path = str(row["relative_path"]).lower()
        if lowered not in name and lowered not in qualname and lowered not in relative_path:
            return (99,)
        if name == lowered:
            bucket = 0
        elif qualname == lowered:
            bucket = 1
        elif name.startswith(lowered):
            bucket = 2
        elif qualname.startswith(lowered):
            bucket = 3
        elif relative_path.startswith(lowered):
            bucket = 4
        else:
            bucket = 5
        return (
            bucket,
            str(row["name"]),
            str(row["relative_path"]),
            int(row["lineno"]),
        )

    matches = [row for row in rows if rank(row)[0] != 99]
    matches.sort(key=rank)
    return matches[:limit]


def load_module_symbols(
    index: LoadedIndex,
    file_id: int,
    *,
    limit: int = 10,
) -> list[dict[str, object]]:
    symbols = [
        build_symbol_row(index, symbol)
        for symbol in index.symbols_by_file_id.get(file_id, [])
    ]
    symbols.sort(key=lambda item: (int(item["lineno"]), str(item["qualname"])))
    return [
        {
            "symbol_type": item["symbol_type"],
            "name": item["name"],
            "qualname": item["qualname"],
            "lineno": item["lineno"],
            "end_lineno": item["end_lineno"],
            "signature": item["signature"],
        }
        for item in symbols[:limit]
    ]


def rows_to_dicts(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [dict(row) for row in rows]


def format_module_results(
    rows: list[dict[str, object]],
    *,
    connection: LoadedIndex | None = None,
    with_symbols: bool = False,
    symbol_limit: int = 10,
) -> str:
    if not rows:
        return "No module matches found."

    lines: list[str] = []
    for index, row in enumerate(rows, start=1):
        lines.append(f"[{index}] {row['module_name']}")
        lines.append(f"    file: {row['relative_path']}")
        lines.append(
            "    counts: "
            f"classes={row['class_count']} "
            f"functions={row['function_count']} "
            f"imports={row['import_count']}"
        )
        if row["parse_error"]:
            lines.append(f"    parse_error: {row['parse_error']}")
        if row["summary"]:
            lines.append(f"    summary: {row['summary']}")
        if with_symbols and connection is not None:
            symbols = load_module_symbols(
                connection,
                int(row["file_id"]),
                limit=symbol_limit,
            )
            if symbols:
                lines.append("    symbols:")
                for symbol in symbols:
                    detail = (
                        f"      - {symbol['qualname']} "
                        f"({symbol['symbol_type']} @ line {symbol['lineno']})"
                    )
                    if symbol["signature"]:
                        detail += f" {symbol['signature']}"
                    lines.append(detail)
        if index != len(rows):
            lines.append("")
    return "\n".join(lines)


def format_symbol_results(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "No symbol matches found."

    lines: list[str] = []
    for index, row in enumerate(rows, start=1):
        lines.append(f"[{index}] {row['qualname']}")
        lines.append(f"    type: {row['symbol_type']}")
        lines.append(f"    file: {row['relative_path']}:{row['lineno']}")
        if row["module_name"]:
            lines.append(f"    module: {row['module_name']}")
        if row["signature"]:
            lines.append(f"    signature: {row['signature']}")
        if row["docstring"]:
            first_line = str(row["docstring"]).splitlines()[0].strip()
            if first_line:
                lines.append(f"    doc: {first_line}")
        if index != len(rows):
            lines.append("")
    return "\n".join(lines)


def build_json_payload(
    command: str,
    query: str,
    rows: list[dict[str, object]],
    *,
    connection: LoadedIndex | None = None,
    with_symbols: bool = False,
    symbol_limit: int = 10,
) -> dict[str, object]:
    result_rows = rows_to_dicts(rows)
    if command == "module" and with_symbols and connection is not None:
        for item in result_rows:
            item["symbols"] = rows_to_dicts(
                load_module_symbols(
                    connection,
                    int(item["file_id"]),
                    limit=symbol_limit,
                )
            )
    return {
        "command": command,
        "query": query,
        "count": len(result_rows),
        "results": result_rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query the project JSON index by module or symbol.",
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_PATH,
        help="JSON index path. Defaults to analysis/project_index.json.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Return machine-readable JSON instead of formatted text.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    module_parser = subparsers.add_parser(
        "module",
        help="Search Python modules by module name or file path.",
    )
    module_parser.add_argument("query", help="Module name, file path, or fragment.")
    module_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to return.",
    )
    module_parser.add_argument(
        "--exact",
        action="store_true",
        help="Match only exact module names or exact file paths.",
    )
    module_parser.add_argument(
        "--with-symbols",
        action="store_true",
        help="Include top symbols for each matched module.",
    )
    module_parser.add_argument(
        "--symbol-limit",
        type=int,
        default=10,
        help="Maximum symbols to show per matched module.",
    )

    symbol_parser = subparsers.add_parser(
        "symbol",
        help="Search symbols by name, qualname, or file path.",
    )
    symbol_parser.add_argument("query", help="Symbol name, qualname, or fragment.")
    symbol_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to return.",
    )
    symbol_parser.add_argument(
        "--exact",
        action="store_true",
        help="Match only exact symbol names or qualnames.",
    )

    return parser


def run_query(args: argparse.Namespace) -> tuple[str, int]:
    if args.db is not None:
        raise RuntimeError(
            "SQLite index is disabled. Use --index analysis/project_index.json instead."
        )

    index_path = args.index.resolve()
    connection = load_index(index_path)
    if args.command == "module":
        rows = search_modules(
            connection,
            args.query,
            limit=args.limit,
            exact=args.exact,
        )
        if args.json:
            payload = build_json_payload(
                "module",
                args.query,
                rows,
                connection=connection,
                with_symbols=args.with_symbols,
                symbol_limit=args.symbol_limit,
            )
            return json.dumps(payload, ensure_ascii=True, indent=2), 0
        return (
            format_module_results(
                rows,
                connection=connection,
                with_symbols=args.with_symbols,
                symbol_limit=args.symbol_limit,
            ),
            0,
        )

    rows = search_symbols(
        connection,
        args.query,
        limit=args.limit,
        exact=args.exact,
    )
    if args.json:
        payload = build_json_payload("symbol", args.query, rows)
        return json.dumps(payload, ensure_ascii=True, indent=2), 0
    return format_symbol_results(rows), 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        output, exit_code = run_query(args)
    except (FileNotFoundError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
