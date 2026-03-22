from __future__ import annotations

import structlog
from pydantic_graph import BaseNode, End, GraphRunContext

from src.graph.state import AnomalyVaguenessResult, ArcraState
from src.services.bedrock import ArcraDeps

logger = structlog.get_logger(__name__)


class ExtractLedgerVarianceNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Entry node: validates the Xero transaction and routes on threshold flags.

    All routing decisions are based on ArcraState.requires_policy_check —
    a pure Python @computed_field.  The LLM is never invoked here
    (PLAN_OVERRIDE #1: Deterministic LLM Guardrails).
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> EvaluateVaguenessNode | End[None]:
        tx = ctx.state.transaction
        logger.info(
            "extract_ledger_variance",
            is_telemetry=True,
            transaction_id=tx.transaction_id,
            node="ExtractLedgerVarianceNode",
            action_summary=(
                f"Ingested: {tx.description} | "
                f"{tx.amount} {tx.currency} | "
                f"requires_policy_check={ctx.state.requires_policy_check} | "
                f"category={ctx.state.policy_category}"
            ),
        )
        if not ctx.state.requires_policy_check:
            ctx.state.status = "normal"
            logger.info(
                "transaction_cleared_normal",
                is_telemetry=True,
                transaction_id=tx.transaction_id,
                node="ExtractLedgerVarianceNode",
                action_summary="Transaction within normal thresholds — ending graph.",
            )
            return End(None)
        return EvaluateVaguenessNode()


class EvaluateVaguenessNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Calls the Bedrock agent to extract text entities and flag missing context.

    Per PLAN_OVERRIDE #1, the LLM only extracts identifiers (project codes,
    attendee lists, asset tags, ATO references).  It never evaluates thresholds.
    The anomaly flag is always set to True upon reaching this node because
    ExtractLedgerVarianceNode already confirmed requires_policy_check=True.
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> End[None]:
        tx = ctx.state.transaction
        logger.info(
            "evaluate_vagueness_start",
            is_telemetry=True,
            transaction_id=tx.transaction_id,
            node="EvaluateVaguenessNode",
            action_summary=f"Calling Bedrock for entity extraction: {tx.description}",
        )
        prompt = (
            f"Transaction ID: {tx.transaction_id}\n"
            f"Description: {tx.description}\n"
            f"Amount: {tx.amount} {tx.currency}\n"
            f"Policy Category: {ctx.state.policy_category}\n\n"
            "Extract any project codes, cost centers, attendee lists, "
            "IT asset tag IDs, ATO reference numbers, or manager approval "
            "references present in the description. "
            "Set is_vague=true if critical identifying context is absent."
        )
        result = await ctx.deps.vagueness_agent.run(prompt)
        vagueness: AnomalyVaguenessResult = result.output
        ctx.state.vagueness_result = vagueness
        ctx.state.anomaly_detected = True
        ctx.state.status = "anomaly_detected"
        logger.info(
            "evaluate_vagueness_complete",
            is_telemetry=True,
            transaction_id=tx.transaction_id,
            node="EvaluateVaguenessNode",
            action_summary=(
                f"Anomaly confirmed | is_vague={vagueness.is_vague} | "
                f"missing_context={vagueness.missing_context}"
            ),
        )
        return End(None)
