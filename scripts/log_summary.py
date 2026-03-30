from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from logicfp.infra.logging.log_summary import format_log_summary, summarize_jsonl_logs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize local logicfp JSONL logs.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="logs/logicfp.jsonl",
        help="Base JSONL log path. Rotated files like .1/.2 are included by default.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only summarize the most recent N events after combining rotated files.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="How many values to show for each summary bucket.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of text.",
    )
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Only read the current log file, skip rotated backups.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = summarize_jsonl_logs(
        Path(args.path),
        limit=args.limit,
        include_rotated=not args.current_only,
    )
    if args.json:
        print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_log_summary(summary, top=args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
