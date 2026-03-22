import asyncio
import json
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.core.db import get_connection

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["transactions"])

_ACTIVE_STATUSES = ("pending", "processing", "suspended")
_PROCESSED_STATUSES = ("resolved", "escalated")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ActiveTransactionsResponse(BaseModel):
    active: list["TransactionSummary"]


class ProcessedTransactionsResponse(BaseModel):
    processed: list["TransactionSummary"]


class TransactionSummary(BaseModel):
    transaction_id: str
    status: str
    amount: float | None = None
    merchant: str | None = None
    employee_name: str | None = None
    confidence_score: float | None = None
    synthesis_reasoning: str | None = None
    last_updated: str


class AuditEvent(BaseModel):
    id: int
    transaction_id: str
    timestamp: str
    node_name: str
    action_summary: str
    slack_channel: str | None = None
    slack_message_sent: str | None = None
    slack_reply_received: str | None = None


class TransactionAuditResponse(BaseModel):
    transaction: TransactionSummary
    audit_trail: list[AuditEvent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_summary(row: object) -> TransactionSummary:
    """Map an aiosqlite Row to a TransactionSummary."""
    return TransactionSummary(
        transaction_id=row["transaction_id"],  # type: ignore[index]
        status=row["status"],  # type: ignore[index]
        amount=row["amount"],  # type: ignore[index]
        merchant=row["merchant"],  # type: ignore[index]
        employee_name=row["employee_name"],  # type: ignore[index]
        confidence_score=row["confidence_score"],  # type: ignore[index]
        synthesis_reasoning=row["synthesis_reasoning"],  # type: ignore[index]
        last_updated=row["last_updated"],  # type: ignore[index]
    )


def _row_to_audit_event(row: object) -> AuditEvent:
    """Map an aiosqlite Row to an AuditEvent."""
    return AuditEvent(
        id=row["id"],  # type: ignore[index]
        transaction_id=row["transaction_id"],  # type: ignore[index]
        timestamp=row["timestamp"],  # type: ignore[index]
        node_name=row["node_name"],  # type: ignore[index]
        action_summary=row["action_summary"],  # type: ignore[index]
        slack_channel=row["slack_channel"],  # type: ignore[index]
        slack_message_sent=row["slack_message_sent"],  # type: ignore[index]
        slack_reply_received=row["slack_reply_received"],  # type: ignore[index]
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/transactions/active", response_model=ActiveTransactionsResponse)
async def get_active_transactions() -> ActiveTransactionsResponse:
    """Return up to 10 transactions in a non-terminal state, newest first."""
    placeholders = ",".join("?" * len(_ACTIVE_STATUSES))
    async with get_connection() as conn:
        cursor = await conn.execute(
            f"SELECT * FROM arcra_ui_read_model WHERE status IN ({placeholders}) "
            f"ORDER BY last_updated DESC LIMIT 10",
            _ACTIVE_STATUSES,
        )
        rows = list(await cursor.fetchall())
    logger.info("active_transactions_queried", count=len(rows))
    return ActiveTransactionsResponse(active=[_row_to_summary(r) for r in rows])


@router.get("/transactions/processed", response_model=ProcessedTransactionsResponse)
async def get_processed_transactions() -> ProcessedTransactionsResponse:
    """Return up to 10 transactions in a terminal state, newest first."""
    placeholders = ",".join("?" * len(_PROCESSED_STATUSES))
    async with get_connection() as conn:
        cursor = await conn.execute(
            f"SELECT * FROM arcra_ui_read_model WHERE status IN ({placeholders}) "
            f"ORDER BY last_updated DESC LIMIT 10",
            _PROCESSED_STATUSES,
        )
        rows = list(await cursor.fetchall())
    logger.info("processed_transactions_queried", count=len(rows))
    return ProcessedTransactionsResponse(processed=[_row_to_summary(r) for r in rows])


@router.get("/transactions/{transaction_id}/audit", response_model=TransactionAuditResponse)
async def get_transaction_audit(transaction_id: str) -> TransactionAuditResponse:
    """Return the read-model row and full chronological audit trail for one transaction."""
    async with get_connection() as conn:
        tx_cursor = await conn.execute(
            "SELECT * FROM arcra_ui_read_model WHERE transaction_id = ?",
            (transaction_id,),
        )
        tx_row = await tx_cursor.fetchone()
        if tx_row is None:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

        audit_cursor = await conn.execute(
            "SELECT * FROM arcra_audit_events WHERE transaction_id = ? ORDER BY timestamp ASC",
            (transaction_id,),
        )
        audit_rows = list(await audit_cursor.fetchall())

    logger.info(
        "transaction_audit_queried",
        transaction_id=transaction_id,
        audit_event_count=len(audit_rows),
    )
    return TransactionAuditResponse(
        transaction=_row_to_summary(tx_row),
        audit_trail=[_row_to_audit_event(r) for r in audit_rows],
    )


# ---------------------------------------------------------------------------
# SSE stream (PLAN_OVERRIDE #4)
# ---------------------------------------------------------------------------


async def _sse_event_generator() -> AsyncGenerator[str, None]:
    """Poll arcra_ui_read_model every second and push SSE events on change."""
    last_updated: str | None = None

    while True:
        try:
            async with get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT MAX(last_updated) AS max_ts FROM arcra_ui_read_model"
                )
                row = await cursor.fetchone()
                current_ts: str | None = row["max_ts"] if row else None

            if current_ts and current_ts != last_updated:
                last_updated = current_ts
                async with get_connection() as conn:
                    cursor = await conn.execute(
                        "SELECT * FROM arcra_ui_read_model ORDER BY last_updated DESC LIMIT 10"
                    )
                    rows = list(await cursor.fetchall())
                payload = json.dumps([_row_to_summary(r).model_dump() for r in rows])
                yield f"data: {payload}\n\n"
                logger.debug("sse_push", record_count=len(rows), last_updated=current_ts)

        except Exception:
            logger.exception("sse_generator_error")

        await asyncio.sleep(1)


@router.get("/stream")
async def stream_transactions() -> StreamingResponse:
    """Server-Sent Events endpoint for real-time dashboard updates (PLAN_OVERRIDE #4)."""
    return StreamingResponse(
        _sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
