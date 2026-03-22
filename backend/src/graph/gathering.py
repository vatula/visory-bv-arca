"""Phase 3 — Evidence Gathering FSM nodes.

PLAN_OVERRIDE #3 applies throughout this module:
  - `SuspendForSlackNode` terminates the graph completely (returns End(None))
    after persisting state to `arcra_checkpoints`.
  - The `/webhook/slack` endpoint starts a *new* graph run from
    `NormalizeToDriveNode` using the loaded state — no in-memory resumption.
"""
from __future__ import annotations

import glob
import json
import time
import uuid
from typing import Union

import structlog
from pydantic_graph import BaseNode, End, GraphRunContext

from src.core.db import (
    load_checkpoint,
    save_checkpoint,
    save_interrupt,
    upsert_ui_read_model,
)
from src.graph.state import ArcraState
from src.services.bedrock import ArcraDeps

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INVOICE_GLOB_PATTERNS: list[str] = ["*.md", "*.pdf"]


def _find_invoice(resources_path: str, transaction_id: str) -> str | None:
    """Search resources/invoices/ for a file whose content contains transaction_id.

    PDF files are matched by filename only (binary content not parsed).
    Returns the file path if found, otherwise None.
    """
    invoices_dir = f"{resources_path}/invoices"
    for pattern in _INVOICE_GLOB_PATTERNS:
        for filepath in glob.glob(f"{invoices_dir}/{pattern}"):
            if filepath.endswith(".md"):
                try:
                    with open(filepath, encoding="utf-8") as fh:
                        if transaction_id in fh.read():
                            return filepath
                except OSError:
                    continue
            else:
                # PDF: match by filename substring
                if transaction_id in filepath:
                    return filepath
    return None


# ---------------------------------------------------------------------------
# Node 1: CheckDriveNode
# ---------------------------------------------------------------------------


class CheckDriveNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Simulate a Google Drive MCP search against resources/invoices/.

    Routes to End if evidence is found, otherwise to DispatchSlackNode.
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> Union[DispatchSlackNode, End[None]]:
        tx_id = ctx.state.transaction.transaction_id
        logger.info(
            "check_drive_start",
            transaction_id=tx_id,
            session_id=ctx.state.session_id,
            is_telemetry=True,
            node="CheckDriveNode",
            action_summary="Searching Drive for invoice evidence",
        )

        invoice_path = _find_invoice(ctx.deps.resources_path, tx_id)

        if invoice_path is not None:
            ctx.state.evidence_documents.append(invoice_path)
            ctx.state.status = "evidence_found"
            logger.info(
                "drive_evidence_found",
                transaction_id=tx_id,
                invoice_path=invoice_path,
                is_telemetry=True,
                node="CheckDriveNode",
                action_summary="Invoice found in Drive; routing to Synthesis",
            )
            await upsert_ui_read_model(
                transaction_id=tx_id,
                status="evidence_found",
                amount=abs(ctx.state.transaction.amount),
                merchant=ctx.state.transaction.description,
            )
            return End(None)

        logger.warning(
            "drive_evidence_missing",
            transaction_id=tx_id,
            is_telemetry=True,
            node="CheckDriveNode",
            action_summary="No invoice found; escalating to Slack",
        )
        return DispatchSlackNode()


# ---------------------------------------------------------------------------
# Node 2: DispatchSlackNode
# ---------------------------------------------------------------------------


class DispatchSlackNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Simulate dispatching a Slack message requesting the missing invoice.

    Records the slack_message_ts in arcra_interrupts and transitions to
    SuspendForSlackNode (PLAN_OVERRIDE #3).
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> SuspendForSlackNode:
        tx_id = ctx.state.transaction.transaction_id
        # Simulate a Slack message timestamp (epoch with microseconds)
        slack_ts = f"{time.time():.6f}"
        ctx.state.slack_thread_ts = slack_ts
        ctx.state.status = "awaiting_slack"

        logger.info(
            "slack_dispatch",
            transaction_id=tx_id,
            slack_thread_ts=slack_ts,
            is_telemetry=True,
            node="DispatchSlackNode",
            action_summary="Slack message dispatched; recording interrupt",
        )

        await save_interrupt(
            thread_id=ctx.state.session_id,
            status="awaiting_slack",
            slack_message_ts=slack_ts,
        )
        await upsert_ui_read_model(
            transaction_id=tx_id,
            status="awaiting_slack",
            amount=abs(ctx.state.transaction.amount),
            merchant=ctx.state.transaction.description,
        )
        return SuspendForSlackNode()


# ---------------------------------------------------------------------------
# Node 3: SuspendForSlackNode  (PLAN_OVERRIDE #3 — terminates the graph)
# ---------------------------------------------------------------------------


class SuspendForSlackNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Persist the full ArcraState to arcra_checkpoints and terminate execution.

    Per PLAN_OVERRIDE #3, this node does NOT use in-memory interrupt().
    It serialises state to SQLite and returns End(None), releasing compute.
    The `/webhook/slack` endpoint will start a *new* graph run.
    """

    async def run(self, ctx: GraphRunContext[ArcraState, ArcraDeps]) -> End[None]:
        checkpoint_id = str(uuid.uuid4())
        state_payload = ctx.state.model_dump(mode="json")

        await save_checkpoint(
            thread_id=ctx.state.session_id,
            checkpoint_id=checkpoint_id,
            checkpoint_data=state_payload,
            metadata={
                "status": "awaiting_slack",
                "transaction_id": ctx.state.transaction.transaction_id,
                "slack_thread_ts": ctx.state.slack_thread_ts,
            },
        )

        logger.info(
            "graph_suspended",
            session_id=ctx.state.session_id,
            checkpoint_id=checkpoint_id,
            slack_thread_ts=ctx.state.slack_thread_ts,
            is_telemetry=True,
            node="SuspendForSlackNode",
            action_summary="Graph state serialised; compute released",
        )
        return End(None)


# ---------------------------------------------------------------------------
# Node 4: NormalizeToDriveNode  (entry point after webhook resume)
# ---------------------------------------------------------------------------


class NormalizeToDriveNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Process the human Slack reply and append evidence to the state.

    This node is the *first* node of the resumption graph run started by
    the `/webhook/slack` endpoint (PLAN_OVERRIDE #3).
    """

    async def run(self, ctx: GraphRunContext[ArcraState, ArcraDeps]) -> End[None]:
        tx_id = ctx.state.transaction.transaction_id
        reply = ctx.state.slack_reply or ""

        # Treat the Slack reply text as inline evidence (URI or free text)
        if reply:
            ctx.state.evidence_documents.append(f"slack_reply://{reply[:200]}")

        ctx.state.status = "evidence_gathered"

        logger.info(
            "normalize_from_slack",
            transaction_id=tx_id,
            evidence_count=len(ctx.state.evidence_documents),
            is_telemetry=True,
            node="NormalizeToDriveNode",
            action_summary="Slack reply normalised; evidence appended",
        )

        await save_interrupt(
            thread_id=ctx.state.session_id,
            status="resumed",
            slack_message_ts=ctx.state.slack_thread_ts,
        )
        await upsert_ui_read_model(
            transaction_id=tx_id,
            status="evidence_gathered",
            amount=abs(ctx.state.transaction.amount),
            merchant=ctx.state.transaction.description,
        )
        return End(None)


# ---------------------------------------------------------------------------
# Public helper: load state from DB checkpoint (used by webhook route)
# ---------------------------------------------------------------------------


async def load_state_from_checkpoint(session_id: str) -> ArcraState | None:
    """Deserialise the most recent ArcraState for *session_id* from SQLite."""
    record = await load_checkpoint(session_id)
    if record is None:
        return None
    raw = record.get("checkpoint")
    if not isinstance(raw, dict):
        try:
            raw = json.loads(str(raw))
        except (ValueError, TypeError):
            return None
    return ArcraState.model_validate(raw)
