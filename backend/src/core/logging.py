import asyncio
import logging
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from src.core.config import get_settings
from src.core.db import insert_audit_event


class TelemetryProcessor:
    """Structlog processor that forks events flagged with is_telemetry=True into SQLite.

    The DB insert is dispatched via asyncio.create_task() so it never blocks FSM node
    execution.  The is_telemetry key is always stripped before the event reaches stdout.
    """

    def __call__(self, logger: WrappedLogger, method: str, event_dict: EventDict) -> EventDict:
        is_telemetry: bool = bool(event_dict.pop("is_telemetry", False))

        if is_telemetry:
            transaction_id: str = str(event_dict.get("transaction_id", "unknown"))
            node_name: str = str(event_dict.get("node", "unknown"))
            action_summary: str = str(event_dict.get("action_summary", event_dict.get("event", "")))
            slack_channel: str | None = event_dict.get("slack_channel")
            slack_message_sent: str | None = event_dict.get("slack_message_sent")
            slack_reply_received: str | None = event_dict.get("slack_reply_received")

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    insert_audit_event(
                        transaction_id=transaction_id,
                        node_name=node_name,
                        action_summary=action_summary,
                        slack_channel=slack_channel,
                        slack_message_sent=slack_message_sent,
                        slack_reply_received=slack_reply_received,
                    ),
                    name=f"telemetry_{transaction_id}_{node_name}",
                )
            except RuntimeError:
                # No running event loop — synchronous context (e.g. test setup).
                # Log the degraded path as a warning without dropping the event.
                structlog.get_logger(__name__).warning(
                    "telemetry_skipped_no_event_loop",
                    transaction_id=transaction_id,
                    node_name=node_name,
                )

        return event_dict


def configure_logging() -> None:
    """Configure structlog with the dual-stream multiplexer.

    Stream 1 → stdout (JSON in production, ConsoleRenderer in development).
    Stream 2 → SQLite arcra_audit_events (via TelemetryProcessor background task).
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        TelemetryProcessor(),
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
