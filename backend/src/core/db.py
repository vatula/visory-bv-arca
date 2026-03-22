import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import aiosqlite
import structlog

from src.core.config import get_settings

logger = structlog.get_logger(__name__)

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS arcra_checkpoints (
    thread_id           TEXT NOT NULL,
    checkpoint_ns       TEXT NOT NULL DEFAULT '',
    checkpoint_id       TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type                TEXT,
    checkpoint          BLOB NOT NULL,
    metadata            BLOB NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS arcra_interrupts (
    thread_id           TEXT PRIMARY KEY,
    status              TEXT NOT NULL,
    slack_message_ts    TEXT,
    expires_at          TIMESTAMP
);

CREATE TABLE IF NOT EXISTS arcra_audit_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id      TEXT NOT NULL,
    timestamp           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    node_name           TEXT NOT NULL,
    action_summary      TEXT NOT NULL,
    slack_channel       TEXT,
    slack_message_sent  TEXT,
    slack_reply_received TEXT
);

CREATE TABLE IF NOT EXISTS arcra_ui_read_model (
    transaction_id      TEXT PRIMARY KEY,
    status              TEXT NOT NULL DEFAULT 'pending',
    amount              REAL,
    merchant            TEXT,
    employee_name       TEXT,
    confidence_score    REAL,
    synthesis_reasoning TEXT,
    last_updated        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db() -> None:
    """Initialise the SQLite database, apply WAL pragmas, and create all tables."""
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as conn:
        await conn.executescript(_DDL)
        await conn.commit()
    logger.info("db_initialised", path=settings.database_url)


@asynccontextmanager
async def get_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield an aiosqlite connection with WAL mode enforced on every open."""
    settings = get_settings()
    async with aiosqlite.connect(settings.database_url) as conn:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = aiosqlite.Row
        yield conn


async def insert_audit_event(
    transaction_id: str,
    node_name: str,
    action_summary: str,
    slack_channel: str | None = None,
    slack_message_sent: str | None = None,
    slack_reply_received: str | None = None,
) -> None:
    """Persist a telemetry audit event.  Called via asyncio.create_task()."""
    try:
        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO arcra_audit_events
                    (transaction_id, timestamp, node_name, action_summary,
                     slack_channel, slack_message_sent, slack_reply_received)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction_id,
                    datetime.now(UTC).isoformat(),
                    node_name,
                    action_summary,
                    slack_channel,
                    slack_message_sent,
                    slack_reply_received,
                ),
            )
            await conn.commit()
    except Exception:
        logger.exception(
            "audit_event_insert_failed",
            transaction_id=transaction_id,
            node_name=node_name,
        )


async def upsert_ui_read_model(
    transaction_id: str,
    status: str,
    amount: float | None = None,
    merchant: str | None = None,
    employee_name: str | None = None,
    confidence_score: float | None = None,
    synthesis_reasoning: str | None = None,
) -> None:
    """Upsert a row in the CQRS read model.  Called via asyncio.create_task()."""
    try:
        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO arcra_ui_read_model
                    (transaction_id, status, amount, merchant, employee_name,
                     confidence_score, synthesis_reasoning, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(transaction_id) DO UPDATE SET
                    status              = excluded.status,
                    amount              = COALESCE(excluded.amount, amount),
                    merchant            = COALESCE(excluded.merchant, merchant),
                    employee_name       = COALESCE(excluded.employee_name, employee_name),
                    confidence_score    = COALESCE(excluded.confidence_score, confidence_score),
                    synthesis_reasoning = COALESCE(excluded.synthesis_reasoning, synthesis_reasoning),
                    last_updated        = excluded.last_updated
                """,
                (
                    transaction_id,
                    status,
                    amount,
                    merchant,
                    employee_name,
                    confidence_score,
                    synthesis_reasoning,
                    datetime.now(UTC).isoformat(),
                ),
            )
            await conn.commit()
    except Exception:
        logger.exception(
            "ui_read_model_upsert_failed",
            transaction_id=transaction_id,
            status=status,
        )


async def save_checkpoint(
    thread_id: str,
    checkpoint_id: str,
    checkpoint_data: object,
    metadata: object,
    checkpoint_ns: str = "",
    parent_checkpoint_id: str | None = None,
    checkpoint_type: str | None = None,
) -> None:
    """Persist a graph state checkpoint."""
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO arcra_checkpoints
                (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id,
                 type, checkpoint, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                thread_id,
                checkpoint_ns,
                checkpoint_id,
                parent_checkpoint_id,
                checkpoint_type,
                json.dumps(checkpoint_data),
                json.dumps(metadata),
            ),
        )
        await conn.commit()
    logger.info(
        "checkpoint_saved",
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        is_telemetry=True,
        node="checkpointer",
        action_summary="Graph state serialised",
    )


async def load_checkpoint(thread_id: str) -> dict[str, object] | None:
    """Load the most recent checkpoint for a given thread_id."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT checkpoint, metadata, checkpoint_id, parent_checkpoint_id, type
            FROM arcra_checkpoints
            WHERE thread_id = ?
            ORDER BY rowid DESC
            LIMIT 1
            """,
            (thread_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "checkpoint": json.loads(row["checkpoint"]),
        "metadata": json.loads(row["metadata"]),
        "checkpoint_id": row["checkpoint_id"],
        "parent_checkpoint_id": row["parent_checkpoint_id"],
        "type": row["type"],
    }


async def save_interrupt(
    thread_id: str,
    status: str,
    slack_message_ts: str | None = None,
    expires_at: datetime | None = None,
) -> None:
    """Upsert an interrupt record (awaiting_slack / resumed)."""
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO arcra_interrupts
                (thread_id, status, slack_message_ts, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                thread_id,
                status,
                slack_message_ts,
                expires_at.isoformat() if expires_at else None,
            ),
        )
        await conn.commit()
    logger.info("interrupt_saved", thread_id=thread_id, status=status)


async def load_interrupt_by_slack_ts(slack_message_ts: str) -> dict[str, object] | None:
    """Load the interrupt record matching a Slack message timestamp."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT thread_id, status, slack_message_ts, expires_at
            FROM arcra_interrupts
            WHERE slack_message_ts = ?
            """,
            (slack_message_ts,),
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "thread_id": row["thread_id"],
        "status": row["status"],
        "slack_message_ts": row["slack_message_ts"],
        "expires_at": row["expires_at"],
    }


async def load_interrupt(thread_id: str) -> dict[str, object] | None:
    """Load the interrupt record for a given thread_id."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT thread_id, status, slack_message_ts, expires_at FROM arcra_interrupts WHERE thread_id = ?",
            (thread_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "thread_id": row["thread_id"],
        "status": row["status"],
        "slack_message_ts": row["slack_message_ts"],
        "expires_at": row["expires_at"],
    }
