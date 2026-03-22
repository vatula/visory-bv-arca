from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.db import upsert_ui_read_model
from src.graph.anomaly import ExtractLedgerVarianceNode
from src.graph.gathering import CheckDriveNode
from src.graph.graphs import anomaly_graph, gathering_graph, policy_graph
from src.graph.policy import QueryNotionNode
from src.graph.state import ArcraState, XeroTransaction
from src.services.bedrock import build_deps_from_settings

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["process"])

# Path is relative to the project root where the FastAPI process is launched.
_RESOURCES_PATH: str = "resources"


class ProcessRequest(BaseModel):
    """Inbound transaction payload for the ARCRA processing pipeline."""

    transaction_id: str
    date: str
    description: str
    amount: float
    currency: str
    type: str
    bank_account_id: str | None = None


class ProcessResponse(BaseModel):
    """Summary of the completed pipeline run for the requesting client."""

    session_id: str
    transaction_id: str
    status: str
    anomaly_detected: bool
    policy_category: str | None
    policy_rules_count: int
    evidence_count: int
    awaiting_slack: bool


@router.post(
    "/process",
    response_model=ProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the full ARCRA pipeline for a single transaction",
)
async def process_transaction(req: ProcessRequest) -> ProcessResponse:
    """Trigger the full Phase 2+3 pipeline:
    1. AnomalyGraph — deterministic threshold check + Bedrock entity extraction.
    2. PolicyGraph (if anomaly) — keyword-routed policy load + Bedrock rule extraction.
    3. GatheringGraph — Drive search; suspend for Slack if evidence missing.
    """
    settings = get_settings()
    tx = XeroTransaction(
        transaction_id=req.transaction_id,
        date=req.date,
        description=req.description,
        amount=req.amount,
        currency=req.currency,
        type=req.type,
    )
    state = ArcraState(session_id=str(uuid.uuid4()), transaction=tx)
    deps = build_deps_from_settings(settings, _RESOURCES_PATH)

    logger.info(
        "process_transaction_start",
        transaction_id=tx.transaction_id,
        session_id=state.session_id,
    )

    try:
        # Phase 2a: Anomaly detection
        anomaly_result = await anomaly_graph.run(
            ExtractLedgerVarianceNode(), state=state, deps=deps
        )
        state = anomaly_result.state

        # Phase 2b: Policy extraction (only when anomaly flagged)
        if state.anomaly_detected:
            policy_result = await policy_graph.run(
                QueryNotionNode(), state=state, deps=deps
            )
            state = policy_result.state

            # Phase 3: Evidence gathering (always runs after policy)
            gathering_result = await gathering_graph.run(
                CheckDriveNode(), state=state, deps=deps
            )
            state = gathering_result.state

    except Exception as exc:
        logger.error(
            "process_transaction_failed",
            transaction_id=tx.transaction_id,
            session_id=state.session_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {exc!s}",
        ) from exc

    await upsert_ui_read_model(
        transaction_id=tx.transaction_id,
        status=state.status,
        amount=abs(tx.amount),
        merchant=tx.description,
    )

    logger.info(
        "process_transaction_complete",
        transaction_id=tx.transaction_id,
        session_id=state.session_id,
        status=state.status,
        anomaly_detected=state.anomaly_detected,
        evidence_count=len(state.evidence_documents),
    )

    return ProcessResponse(
        session_id=state.session_id,
        transaction_id=tx.transaction_id,
        status=state.status,
        anomaly_detected=state.anomaly_detected,
        policy_category=str(state.policy_category) if state.policy_category else None,
        policy_rules_count=len(state.policy_context),
        evidence_count=len(state.evidence_documents),
        awaiting_slack=state.status == "awaiting_slack",
    )
