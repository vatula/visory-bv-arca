"""Slack webhook endpoint — Phase 3 resumption logic.

Per PLAN_OVERRIDE #3, this endpoint does NOT resume an in-memory graph.
It loads the serialised ArcraState from SQLite, injects the human reply,
and starts a *new* graph run from NormalizeToDriveNode.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.core.db import load_interrupt_by_slack_ts, upsert_ui_read_model
from src.graph.gathering import NormalizeToDriveNode, load_state_from_checkpoint
from src.graph.graphs import resumption_graph
from src.services.bedrock import build_deps_from_settings
from src.core.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["webhook"])

_RESOURCES_PATH: str = "resources"


class SlackWebhookPayload(BaseModel):
    """Inbound payload from the Slack webhook simulation."""

    slack_message_ts: str
    reply_text: str


class SlackWebhookResponse(BaseModel):
    """Summary returned after successfully resuming the graph."""

    session_id: str
    transaction_id: str
    status: str
    evidence_count: int


@router.post(
    "/webhook/slack",
    response_model=SlackWebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive a Slack reply and resume the suspended ARCRA graph",
)
async def slack_webhook(payload: SlackWebhookPayload) -> SlackWebhookResponse:
    """PLAN_OVERRIDE #3 resumption flow:
    1. Look up the suspended session via slack_message_ts.
    2. Load the serialised ArcraState from arcra_checkpoints.
    3. Inject the human reply into state.slack_reply.
    4. Start a new resumption_graph run from NormalizeToDriveNode.
    """
    logger.info(
        "slack_webhook_received",
        slack_message_ts=payload.slack_message_ts,
    )

    # 1. Resolve thread_id from slack_message_ts
    interrupt_record = await load_interrupt_by_slack_ts(payload.slack_message_ts)
    if interrupt_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No suspended session found for slack_message_ts={payload.slack_message_ts!r}",
        )

    thread_id = str(interrupt_record["thread_id"])

    # 2. Load serialised state
    state = await load_state_from_checkpoint(thread_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No checkpoint found for session_id={thread_id!r}",
        )

    # 3. Inject human reply
    state.slack_reply = payload.reply_text

    logger.info(
        "slack_graph_resuming",
        session_id=thread_id,
        transaction_id=state.transaction.transaction_id,
        is_telemetry=True,
        node="SlackWebhook",
        action_summary="Resuming graph with human Slack reply",
    )

    settings = get_settings()
    deps = build_deps_from_settings(settings, _RESOURCES_PATH)

    # 4. New graph run from NormalizeToDriveNode (PLAN_OVERRIDE #3)
    try:
        result = await resumption_graph.run(
            NormalizeToDriveNode(), state=state, deps=deps
        )
        state = result.state
    except Exception as exc:
        logger.error(
            "slack_graph_resume_failed",
            session_id=thread_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph resumption failed: {exc!s}",
        ) from exc

    await upsert_ui_read_model(
        transaction_id=state.transaction.transaction_id,
        status=state.status,
        amount=abs(state.transaction.amount),
        merchant=state.transaction.description,
    )

    logger.info(
        "slack_webhook_complete",
        session_id=thread_id,
        status=state.status,
        evidence_count=len(state.evidence_documents),
    )

    return SlackWebhookResponse(
        session_id=thread_id,
        transaction_id=state.transaction.transaction_id,
        status=state.status,
        evidence_count=len(state.evidence_documents),
    )
