from __future__ import annotations

from pathlib import Path

from logicfp import create_protector
from logicfp.domain.models import HandlerRequest
from logicfp.infra.logging import JsonlEventLogger, MultiEventLogger, SummaryLogger
from logicfp.user_mode import get_ai_error


LOG_PATH = Path("logs/logicfp.jsonl")
jsonl_logger = JsonlEventLogger(LOG_PATH, max_bytes=16_384, backup_count=3)


event_logger = MultiEventLogger(
    jsonl_logger,
    SummaryLogger(every_n=2, sink=jsonl_logger),
)


protector = create_protector(
    default_source="local_logging_demo",
    event_logger=event_logger,
)


@protector.protect(simple=False)
def summarize_release_notes(request: HandlerRequest) -> dict[str, object]:
    raise RuntimeError("OpenAI upstream is temporarily overloaded")


def run_demo() -> dict[str, object]:
    result = summarize_release_notes(payload={"topic": "release-notes"})
    ai_error = get_ai_error(result)
    return {
        "result": result,
        "ai_error": ai_error,
        "log_path": str(LOG_PATH),
    }


def main() -> None:
    print(run_demo())
    event_logger.flush()


if __name__ == "__main__":
    main()
