from __future__ import annotations

import os

import structlog
from pydantic_graph import BaseNode, End, GraphRunContext

from src.graph.state import ArcraState, PolicyRule, POLICY_FILE_MAP
from src.services.bedrock import ArcraDeps

logger = structlog.get_logger(__name__)

# Max characters from a policy file passed to the LLM — PLAN_OVERRIDE #5
_POLICY_CONTENT_MAX_CHARS: int = 2000


class QueryNotionNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Loads the relevant policy file using deterministic keyword routing.

    Simulates the Notion MCP server by reading from resources/policies/*.md.
    Per PLAN_OVERRIDE #5, only the single matched policy file is loaded —
    never the entire corpus.
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> ExtractRulesNode | EscalateNode:
        tx_id = ctx.state.transaction.transaction_id
        category = ctx.state.policy_category
        if category is None or category not in POLICY_FILE_MAP:
            logger.warning(
                "policy_category_unmapped",
                is_telemetry=True,
                transaction_id=tx_id,
                node="QueryNotionNode",
                action_summary=(
                    f"No policy file mapped for category={category!r}. Escalating."
                ),
            )
            ctx.state.status = "escalated"
            ctx.state.error_message = f"No policy mapped for category: {category}"
            return EscalateNode()
        policy_filename = POLICY_FILE_MAP[category]
        policy_path = os.path.join(
            ctx.deps.resources_path, "policies", policy_filename
        )
        if not os.path.exists(policy_path):
            logger.error(
                "policy_file_missing",
                is_telemetry=True,
                transaction_id=tx_id,
                node="QueryNotionNode",
                action_summary=f"Policy file not found on disk: {policy_path}",
            )
            ctx.state.status = "escalated"
            ctx.state.error_message = f"Policy file missing: {policy_filename}"
            return EscalateNode()
        ctx.state.policy_file_path = policy_path
        logger.info(
            "policy_file_loaded",
            is_telemetry=True,
            transaction_id=tx_id,
            node="QueryNotionNode",
            action_summary=(
                f"Loaded policy={policy_filename} for category={category}"
            ),
        )
        return ExtractRulesNode()


class ExtractRulesNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Extracts structured compliance rules from the loaded policy via Bedrock.

    Per PLAN_OVERRIDE #1, the LLM only extracts rules explicitly stated in the
    document.  Per PLAN_OVERRIDE #5, input is capped at 2000 chars to prevent
    context blowout.
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> End[None] | EscalateNode:
        tx = ctx.state.transaction
        tx_id = tx.transaction_id
        policy_path = ctx.state.policy_file_path
        if policy_path is None:
            logger.error(
                "policy_path_missing_in_state",
                is_telemetry=True,
                transaction_id=tx_id,
                node="ExtractRulesNode",
                action_summary="policy_file_path is None — cannot extract rules.",
            )
            ctx.state.status = "escalated"
            ctx.state.error_message = "Policy path missing in state"
            return EscalateNode()
        with open(policy_path) as fh:
            raw_policy = fh.read(_POLICY_CONTENT_MAX_CHARS)
        prompt = (
            f"Policy Document (excerpt):\n{raw_policy}\n\n"
            f"Transaction: {tx.description} | "
            f"Amount: {tx.amount} {tx.currency} | "
            f"Category: {ctx.state.policy_category}\n\n"
            "Extract all actionable compliance rules from the policy that apply "
            "to this transaction. Return a JSON object with a 'rules' array."
        )
        try:
            result = await ctx.deps.policy_extraction_agent.run(prompt)
            rules: list[PolicyRule] = result.output.rules
            ctx.state.policy_context = rules
            ctx.state.status = "policy_extracted"
            logger.info(
                "policy_rules_extracted",
                is_telemetry=True,
                transaction_id=tx_id,
                node="ExtractRulesNode",
                action_summary=(
                    f"Extracted {len(rules)} rules for "
                    f"category={ctx.state.policy_category}"
                ),
            )
            return End(None)
        except Exception as exc:
            logger.error(
                "policy_extraction_failed",
                is_telemetry=True,
                transaction_id=tx_id,
                node="ExtractRulesNode",
                action_summary=f"Bedrock call failed: {exc!s}",
                exc_info=True,
            )
            ctx.state.status = "escalated"
            ctx.state.error_message = f"LLM extraction failed: {exc!s}"
            return EscalateNode()


class EscalateNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Terminal escalation node — queues the transaction for human review."""

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> End[None]:
        tx_id = ctx.state.transaction.transaction_id
        ctx.state.status = "escalated"
        logger.warning(
            "transaction_escalated",
            is_telemetry=True,
            transaction_id=tx_id,
            node="EscalateNode",
            action_summary=(
                f"Escalated for human review. "
                f"Reason: {ctx.state.error_message}"
            ),
        )
        return End(None)
