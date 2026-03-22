from __future__ import annotations

import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel

from src.core.db import get_connection

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["reset"])


class ResetResponse(BaseModel):
    message: str
    rows_deleted_ui_read_model: int
    rows_deleted_audit_events: int


@router.post(
    "/reset",
    response_model=ResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset application state — clears all processed transactions and audit events",
)
async def reset_state() -> ResetResponse:
    """Truncate arcra_ui_read_model and arcra_audit_events so the pipeline
    can be replayed from scratch via the queue endpoint."""
    async with get_connection() as conn:
        cursor_ui = await conn.execute("DELETE FROM arcra_ui_read_model")
        rows_ui: int = cursor_ui.rowcount if cursor_ui.rowcount >= 0 else 0

        cursor_audit = await conn.execute("DELETE FROM arcra_audit_events")
        rows_audit: int = cursor_audit.rowcount if cursor_audit.rowcount >= 0 else 0

        await conn.commit()

    logger.info(
        "state_reset",
        rows_deleted_ui_read_model=rows_ui,
        rows_deleted_audit_events=rows_audit,
        is_telemetry=True,
    )

    return ResetResponse(
        message="Application state reset successfully.",
        rows_deleted_ui_read_model=rows_ui,
        rows_deleted_audit_events=rows_audit,
    )
