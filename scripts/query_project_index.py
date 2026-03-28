from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB_PATH = Path("analysis") / "project_index.sqlite"


def escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def connect_database(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite index not found: {db_path}")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    required_tables = {"files", "python_modules", "symbols", "imports"}
    table_names = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        )
    }
    missing = required_tables - table_names
    if missing:
        connection.close()
        raise RuntimeError(
            "SQLite index is missing required tables: "
            + ", ".join(sorted(missing))
        )
    return connection


def search_modules(
    connection: sqlite3.Connection,
    query: str,
    *,
    limit: int = 10,
    exact: bool = False,
) -> list[sqlite3.Row]:
    lowered = query.lower()
    if exact:
        sql = """
        SELECT
            files.id AS file_id,
            files.relative_path,
            files.summary,
            python_modules.module_name,
            python_modules.class_count,
            python_modules.function_count,
            python_modules.import_count,
            python_modules.parse_error
        FROM python_modules
        JOIN files ON files.id = python_modules.file_id
        WHERE LOWER(python_modules.module_name) = ?
           OR LOWER(files.relative_path) = ?
        ORDER BY python_modules.module_name, files.relative_path
        LIMIT ?
        """
        params = (lowered, lowered, limit)
    else:
        pattern = f"%{escape_like(lowered)}%"
        prefix = f"{escape_like(lowered)}%"
        sql = """
        SELECT
            files.id AS file_id,
            files.relative_path,
            files.summary,
            python_modules.module_name,
            python_modules.class_count,
            python_modules.function_count,
            python_modules.import_count,
            python_modules.parse_error
        FROM python_modules
        JOIN files ON files.id = python_modules.file_id
        WHERE LOWER(python_modules.module_name) LIKE ? ESCAPE '\\'
           OR LOWER(files.relative_path) LIKE ? ESCAPE '\\'
           OR LOWER(files.file_name) LIKE ? ESCAPE '\\'
        ORDER BY
            CASE
                WHEN LOWER(python_modules.module_name) = ? THEN 0
                WHEN LOWER(files.relative_path) = ? THEN 1
                WHEN LOWER(python_modules.module_name) LIKE ? ESCAPE '\\' THEN 2
                WHEN LOWER(files.relative_path) LIKE ? ESCAPE '\\' THEN 3
                WHEN LOWER(files.file_name) LIKE ? ESCAPE '\\' THEN 4
                ELSE 5
            END,
            python_modules.import_count DESC,
            python_modules.function_count DESC,
            files.relative_path
        LIMIT ?
        """
        params = (
            pattern,
            pattern,
            pattern,
            lowered,
            lowered,
            prefix,
            prefix,
            prefix,
            limit,
        )
    return list(connection.execute(sql, params))


def search_symbols(
    connection: sqlite3.Connection,
    query: str,
    *,
    limit: int = 10,
    exact: bool = False,
) -> list[sqlite3.Row]:
    lowered = query.lower()
    if exact:
        sql = """
        SELECT
            symbols.id,
            symbols.symbol_type,
            symbols.name,
            symbols.qualname,
            symbols.lineno,
            symbols.end_lineno,
            symbols.signature,
            symbols.docstring,
            files.id AS file_id,
            files.relative_path,
            python_modules.module_name
        FROM symbols
        JOIN files ON files.id = symbols.file_id
        LEFT JOIN python_modules ON python_modules.file_id = files.id
        WHERE LOWER(symbols.name) = ?
           OR LOWER(symbols.qualname) = ?
        ORDER BY symbols.qualname, files.relative_path, symbols.lineno
        LIMIT ?
        """
        params = (lowered, lowered, limit)
    else:
        pattern = f"%{escape_like(lowered)}%"
        prefix = f"{escape_like(lowered)}%"
        sql = """
        SELECT
            symbols.id,
            symbols.symbol_type,
            symbols.name,
            symbols.qualname,
            symbols.lineno,
            symbols.end_lineno,
            symbols.signature,
            symbols.docstring,
            files.id AS file_id,
            files.relative_path,
            python_modules.module_name
        FROM symbols
        JOIN files ON files.id = symbols.file_id
        LEFT JOIN python_modules ON python_modules.file_id = files.id
        WHERE LOWER(symbols.name) LIKE ? ESCAPE '\\'
           OR LOWER(symbols.qualname) LIKE ? ESCAPE '\\'
           OR LOWER(files.relative_path) LIKE ? ESCAPE '\\'
        ORDER BY
            CASE
                WHEN LOWER(symbols.name) = ? THEN 0
                WHEN LOWER(symbols.qualname) = ? THEN 1
                WHEN LOWER(symbols.name) LIKE ? ESCAPE '\\' THEN 2
                WHEN LOWER(symbols.qualname) LIKE ? ESCAPE '\\' THEN 3
                WHEN LOWER(files.relative_path) LIKE ? ESCAPE '\\' THEN 4
                ELSE 5
            END,
            symbols.name,
            files.relative_path,
            symbols.lineno
        LIMIT ?
        """
        params = (
            pattern,
            pattern,
            pattern,
            lowered,
            lowered,
            prefix,
            prefix,
            prefix,
            limit,
        )
    return list(connection.execute(sql, params))


def load_module_symbols(
    connection: sqlite3.Connection,
    file_id: int,
    *,
    limit: int = 10,
) -> list[sqlite3.Row]:
    sql = """
    SELECT
        symbol_type,
        name,
        qualname,
        lineno,
        end_lineno,
        signature
    FROM symbols
    WHERE file_id = ?
    ORDER BY lineno, qualname
    LIMIT ?
    """
    return list(connection.execute(sql, (file_id, limit)))


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, object]]:
    return [dict(row) for row in rows]


def format_module_results(
    rows: list[sqlite3.Row],
    *,
    connection: sqlite3.Connection | None = None,
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
                row["file_id"],
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


def format_symbol_results(rows: list[sqlite3.Row]) -> str:
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
            first_line = row["docstring"].splitlines()[0].strip()
            if first_line:
                lines.append(f"    doc: {first_line}")
        if index != len(rows):
            lines.append("")
    return "\n".join(lines)


def build_json_payload(
    command: str,
    query: str,
    rows: list[sqlite3.Row],
    *,
    connection: sqlite3.Connection | None = None,
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
        description="Query the project SQLite index by module or symbol.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="SQLite index path. Defaults to analysis/project_index.sqlite.",
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
    db_path = args.db.resolve()
    connection = connect_database(db_path)
    try:
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
    finally:
        connection.close()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        output, exit_code = run_query(args)
    except (FileNotFoundError, RuntimeError, sqlite3.DatabaseError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
