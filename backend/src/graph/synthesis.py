from __future__ import annotations

import structlog
from pydantic_graph import BaseNode, End, GraphRunContext

from src.graph.state import ArcraState, SynthesisEvaluation, XeroDraft
from src.services.bedrock import ArcraDeps

logger = structlog.get_logger(__name__)


class MergeContextNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Pure assembly node: merges transaction, policy, and evidence into a
    single context string for the downstream LLM evaluation.

    No I/O — this node is mathematically pure (AGENTS.md purity rule).
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> EvaluateConfidenceNode:
        state = ctx.state
        parts: list[str] = [
            f"Transaction: {state.transaction.description}",
            f"Amount: {state.transaction.amount} {state.transaction.currency}",
            f"Date: {state.transaction.date}",
        ]
        if state.vagueness_result:
            parts.append(f"Vagueness: {state.vagueness_result.missing_context}")
            if state.vagueness_result.extracted_entities:
                parts.append(f"Entities: {state.vagueness_result.extracted_entities}")
        if state.policy_context:
            rules_text = "; ".join(r.description for r in state.policy_context[:5])
            parts.append(f"Policy rules: {rules_text}")
        if state.evidence_documents:
            parts.append(f"Evidence: {', '.join(state.evidence_documents)}")
        if state.slack_reply:
            parts.append(f"Slack reply: {state.slack_reply}")

        state.merged_context = "\n".join(parts)

        logger.info(
            "synthesis_context_merged",
            session_id=state.session_id,
            policy_rules=len(state.policy_context),
            evidence_docs=len(state.evidence_documents),
            is_telemetry=True,
        )
        return EvaluateConfidenceNode()


class EvaluateConfidenceNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Calls the Bedrock synthesis agent to produce a confidence score and
    reasoning string, then routes to DraftGenerationNode or
    EscalateToHumanReviewNode based on the configured threshold.
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> DraftGenerationNode | EscalateToHumanReviewNode:
        state = ctx.state
        prompt = state.merged_context or (
            f"Transaction: {state.transaction.description} "
            f"Amount: {state.transaction.amount} {state.transaction.currency}"
        )

        try:
            result = await ctx.deps.synthesis_agent.run(prompt)
            evaluation: SynthesisEvaluation = result.output
        except Exception:
            logger.warning(
                "synthesis_agent_fallback",
                session_id=state.session_id,
                exc_info=True,
            )
            evaluation = SynthesisEvaluation(
                confidence_score=0.0,
                reasoning="LLM call failed; defaulting to escalation.",
                key_risks=["llm_failure"],
            )

        state.synthesis_evaluation = evaluation
        # PLAN_OVERRIDE #1: threshold comparison is pure Python, not LLM
        threshold = ctx.deps.confidence_threshold

        logger.info(
            "synthesis_confidence_evaluated",
            session_id=state.session_id,
            confidence_score=evaluation.confidence_score,
            threshold=threshold,
            routes_to_draft=evaluation.confidence_score >= threshold,
            is_telemetry=True,
        )

        if evaluation.confidence_score >= threshold:
            return DraftGenerationNode()
        return EscalateToHumanReviewNode()


class DraftGenerationNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Assembles the Xero ledger draft payload from the fully-populated state
    and simulates an MCP push to Xero (prototype: no live API call).
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> MarkCompleteNode:
        state = ctx.state
        evaluation = state.synthesis_evaluation

        draft = XeroDraft(
            transaction_id=state.transaction.transaction_id,
            merchant=state.transaction.description,
            amount=abs(state.transaction.amount),
            currency=state.transaction.currency,
            category=str(state.policy_category) if state.policy_category else None,
            policy_references=[r.rule_id for r in state.policy_context],
            evidence_uris=list(state.evidence_documents),
            confidence_score=evaluation.confidence_score if evaluation else 0.0,
            reasoning=evaluation.reasoning if evaluation else "",
        )
        state.xero_draft = draft

        logger.info(
            "xero_draft_generated",
            session_id=state.session_id,
            draft_id=draft.draft_id,
            transaction_id=draft.transaction_id,
            confidence_score=draft.confidence_score,
            is_telemetry=True,
        )
        return MarkCompleteNode()


class EscalateToHumanReviewNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Flags the transaction for human review when confidence falls below the
    configured threshold.  Updates the status so the CQRS read model and UI
    can surface it to the human auditor.
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> End[None]:
        state = ctx.state
        state.status = "escalated"
        reasoning = (
            state.synthesis_evaluation.reasoning
            if state.synthesis_evaluation
            else "Confidence below threshold"
        )
        state.error_message = f"Escalated for human review: {reasoning}"

        logger.info(
            "synthesis_escalated",
            session_id=state.session_id,
            confidence_score=(
                state.synthesis_evaluation.confidence_score
                if state.synthesis_evaluation
                else None
            ),
            threshold=ctx.deps.confidence_threshold,
            is_telemetry=True,
        )
        return End(None)


class MarkCompleteNode(BaseNode[ArcraState, ArcraDeps, None]):
    """Terminal node for the happy path.  Sets status to 'completed' and
    terminates graph execution cleanly.
    """

    async def run(
        self, ctx: GraphRunContext[ArcraState, ArcraDeps]
    ) -> End[None]:
        state = ctx.state
        state.status = "completed"

        logger.info(
            "synthesis_complete",
            session_id=state.session_id,
            draft_id=state.xero_draft.draft_id if state.xero_draft else None,
            status=state.status,
            is_telemetry=True,
        )
        return End(None)
