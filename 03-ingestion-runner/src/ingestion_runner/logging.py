from __future__ import annotations

from collections.abc import MutableSequence
from typing import Any

import structlog


def configure_json_logging(events: MutableSequence[dict[str, Any]] | None = None) -> None:
    processors: list[Any] = [
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.add_log_level,
    ]
    if events is None:
        processors.append(structlog.processors.JSONRenderer())
        structlog.configure(processors=processors, cache_logger_on_first_use=False)
        return

    def capture(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        events.append(dict(event_dict))
        return event_dict

    processors.append(capture)
    structlog.configure(
        processors=processors,
        logger_factory=structlog.ReturnLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger() -> Any:
    return structlog.get_logger("ingestion_runner")
