"""Phase 4 tests — Synthesis & Xero Draft FSM.

All transaction fixtures are loaded from resources/xero_api_feed.json
(AGENTS.md §4 — no dummy dicts).  Bedrock synthesis agent is mocked via
pydantic_ai TestModel so no AWS credentials are required.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from src.graph.graphs import synthesis_graph
from src.graph.state import (
    AnomalyVaguenessResult,
    ArcraState,
    PolicyRule,
    PolicyRuleContainer,
    SynthesisEvaluation,
    XeroDraft,
    XeroTransaction,
)
from src.graph.synthesis import (
    DraftGenerationNode,
    EscalateToHumanReviewNode,
    EvaluateConfidenceNode,
    MarkCompleteNode,
    MergeContextNode,
)
from src.services.bedrock import ArcraDeps

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RESOURCES_PATH = str(Path(__file__).parents[2] / "resources")
_FEED_PATH = Path(_RESOURCES_PATH) / "xero_api_feed.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_transactions() -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(_FEED_PATH.read_text())
    txns: list[dict[str, Any]] = []
    for account in data:
        for tx in account["transactions"]:
            txns.append(tx)
    return txns


def _make_tx(**kwargs: object) -> XeroTransaction:
    defaults: dict[str, object] = {
        "transaction_id": "tx_100001",
        "date": "2026-03-17",
        "description": "AWS EMEA SARL",
        "amount": -890.0,
        "currency": "AUD",
        "type": "debit",
    }
    defaults.update(kwargs)
    return XeroTransaction.model_validate(defaults)


def _make_state(**kwargs: object) -> ArcraState:
    tx = kwargs.pop("transaction", _make_tx())
    return ArcraState(transaction=tx, **kwargs)  # type: ignore[arg-type]


def _mock_synthesis_agent(
    confidence: float = 0.9,
    reasoning: str = "All policy criteria satisfied.",
    key_risks: list[str] | None = None,
) -> Any:
    """Return an AsyncMock agent that yields a deterministic SynthesisEvaluation."""
    evaluation = SynthesisEvaluation(
        confidence_score=confidence,
        reasoning=reasoning,
        key_risks=key_risks or [],
    )
    result = AsyncMock()
    result.output = evaluation
    mock = AsyncMock()
    mock.run = AsyncMock(return_value=result)
    return mock


def _make_deps(
    synthesis_agent: Any | None = None,
    confidence_threshold: float = 0.75,
) -> ArcraDeps:
    return ArcraDeps(
        db_path=":memory:",
        resources_path=_RESOURCES_PATH,
        vagueness_agent=Agent(TestModel(), output_type=AnomalyVaguenessResult),
        policy_extraction_agent=Agent(TestModel(), output_type=PolicyRuleContainer),
        synthesis_agent=synthesis_agent or _mock_synthesis_agent(),
        confidence_threshold=confidence_threshold,
    )


# ---------------------------------------------------------------------------
# 1. MergeContextNode — pure assembly (no I/O)
# ---------------------------------------------------------------------------

class TestMergeContextNode:
    @pytest.mark.asyncio
    async def test_merge_populates_merged_context(self) -> None:
        state = _make_state()
        deps = _make_deps()
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.merged_context is not None
        assert "AWS EMEA SARL" in result.state.merged_context

    @pytest.mark.asyncio
    async def test_merge_includes_policy_rules(self) -> None:
        rule = PolicyRule(category="cloud", description="Requires project code")
        state = _make_state(policy_context=[rule])
        deps = _make_deps()
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert "Requires project code" in (result.state.merged_context or "")

    @pytest.mark.asyncio
    async def test_merge_includes_evidence_documents(self) -> None:
        state = _make_state(evidence_documents=["resources/invoices/acc_1001_1.md"])
        deps = _make_deps()
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert "acc_1001_1.md" in (result.state.merged_context or "")

    @pytest.mark.asyncio
    async def test_merge_includes_slack_reply(self) -> None:
        state = _make_state(slack_reply="Approved by finance team")
        deps = _make_deps()
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert "Approved by finance team" in (result.state.merged_context or "")

    @pytest.mark.asyncio
    async def test_merge_includes_vagueness_result(self) -> None:
        vagueness = AnomalyVaguenessResult(
            is_vague=True,
            missing_context="No project code found",
        )
        state = _make_state(vagueness_result=vagueness)
        deps = _make_deps()
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert "No project code found" in (result.state.merged_context or "")


# ---------------------------------------------------------------------------
# 2. EvaluateConfidenceNode — routing logic
# ---------------------------------------------------------------------------

class TestEvaluateConfidenceNode:
    @pytest.mark.asyncio
    async def test_high_confidence_routes_to_draft(self) -> None:
        state = _make_state()
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.95))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.synthesis_evaluation is not None
        assert result.state.synthesis_evaluation.confidence_score == 0.95
        assert result.state.xero_draft is not None
        assert result.state.status == "completed"

    @pytest.mark.asyncio
    async def test_low_confidence_routes_to_escalation(self) -> None:
        state = _make_state()
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.3))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.status == "escalated"
        assert result.state.xero_draft is None

    @pytest.mark.asyncio
    async def test_confidence_exactly_at_threshold_routes_to_draft(self) -> None:
        """Boundary: score == threshold must pass (>=)."""
        state = _make_state()
        deps = _make_deps(
            synthesis_agent=_mock_synthesis_agent(confidence=0.75),
            confidence_threshold=0.75,
        )
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.status == "completed"
        assert result.state.xero_draft is not None

    @pytest.mark.asyncio
    async def test_confidence_just_below_threshold_escalates(self) -> None:
        """Boundary: score just below threshold must escalate."""
        state = _make_state()
        deps = _make_deps(
            synthesis_agent=_mock_synthesis_agent(confidence=0.74),
            confidence_threshold=0.75,
        )
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.status == "escalated"

    @pytest.mark.asyncio
    async def test_agent_failure_defaults_to_escalation(self) -> None:
        """When the synthesis agent raises, EvaluateConfidenceNode must fall back
        to confidence=0.0 and route to EscalateToHumanReviewNode."""
        failing_agent = AsyncMock()
        failing_agent.run = AsyncMock(side_effect=RuntimeError("Bedrock unavailable"))
        state = _make_state()
        deps = _make_deps(synthesis_agent=failing_agent)
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.status == "escalated"
        assert result.state.synthesis_evaluation is not None
        assert result.state.synthesis_evaluation.confidence_score == 0.0
        assert "llm_failure" in result.state.synthesis_evaluation.key_risks


# ---------------------------------------------------------------------------
# 3. DraftGenerationNode — XeroDraft payload
# ---------------------------------------------------------------------------

class TestDraftGenerationNode:
    @pytest.mark.asyncio
    async def test_draft_has_correct_transaction_id(self) -> None:
        tx = _make_tx(transaction_id="tx_DRAFT_001")
        state = _make_state(transaction=tx)
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.9))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.xero_draft is not None
        assert result.state.xero_draft.transaction_id == "tx_DRAFT_001"

    @pytest.mark.asyncio
    async def test_draft_carries_evidence_uris(self) -> None:
        state = _make_state(
            evidence_documents=["resources/invoices/acc_1001_1.md"],
        )
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.9))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        draft = result.state.xero_draft
        assert draft is not None
        assert "resources/invoices/acc_1001_1.md" in draft.evidence_uris

    @pytest.mark.asyncio
    async def test_draft_carries_policy_references(self) -> None:
        rule = PolicyRule(
            rule_id="rule-uuid-001",
            category="cloud",
            description="Requires project code",
        )
        state = _make_state(policy_context=[rule])
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.9))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        draft = result.state.xero_draft
        assert draft is not None
        assert "rule-uuid-001" in draft.policy_references

    @pytest.mark.asyncio
    async def test_draft_amount_is_absolute(self) -> None:
        """Draft amount must always be positive regardless of debit sign."""
        tx = _make_tx(amount=-1250.0)
        state = _make_state(transaction=tx)
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.9))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.xero_draft is not None
        assert result.state.xero_draft.amount == 1250.0

    @pytest.mark.asyncio
    async def test_draft_xero_status_is_draft(self) -> None:
        state = _make_state()
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.9))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.xero_draft is not None
        assert result.state.xero_draft.xero_status == "draft"


# ---------------------------------------------------------------------------
# 4. EscalateToHumanReviewNode
# ---------------------------------------------------------------------------

class TestEscalateToHumanReviewNode:
    @pytest.mark.asyncio
    async def test_escalation_sets_error_message(self) -> None:
        state = _make_state()
        deps = _make_deps(
            synthesis_agent=_mock_synthesis_agent(
                confidence=0.1, reasoning="Missing attendees list"
            )
        )
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.error_message is not None
        assert "Missing attendees list" in result.state.error_message

    @pytest.mark.asyncio
    async def test_escalation_does_not_produce_draft(self) -> None:
        state = _make_state()
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.0))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.xero_draft is None


# ---------------------------------------------------------------------------
# 5. Integration — real xero_api_feed.json transactions
# ---------------------------------------------------------------------------

class TestSynthesisIntegration:
    @pytest.mark.asyncio
    async def test_cloud_transaction_completes_with_high_confidence(self) -> None:
        """tx_100001 (AWS EMEA SARL, -$890) should produce a draft at high confidence."""
        txns = _load_transactions()
        tx_data = next(t for t in txns if t["transaction_id"] == "tx_100001")
        tx = XeroTransaction.model_validate(tx_data)
        state = ArcraState(
            transaction=tx,
            anomaly_detected=True,
            evidence_documents=["resources/invoices/acc_1001_1.md"],
        )
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.88))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.status == "completed"
        assert result.state.xero_draft is not None
        assert result.state.xero_draft.transaction_id == "tx_100001"

    @pytest.mark.asyncio
    async def test_entertainment_transaction_escalates_at_low_confidence(self) -> None:
        """Entertainment transaction with no evidence should escalate."""
        txns = _load_transactions()
        tx_data = next(
            (
                t for t in txns
                if "cafe" in t["description"].lower()
                or "restaurant" in t["description"].lower()
                or "uber eats" in t["description"].lower()
            ),
            txns[0],
        )
        tx = XeroTransaction.model_validate(tx_data)
        state = ArcraState(transaction=tx, anomaly_detected=True)
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.4))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.status == "escalated"

    @pytest.mark.asyncio
    async def test_synthesis_evaluation_stored_on_state(self) -> None:
        """SynthesisEvaluation must always be persisted on state after the graph."""
        txns = _load_transactions()
        tx = XeroTransaction.model_validate(txns[0])
        state = ArcraState(transaction=tx)
        deps = _make_deps(synthesis_agent=_mock_synthesis_agent(confidence=0.82))
        result = await synthesis_graph.run(MergeContextNode(), state=state, deps=deps)
        assert result.state.synthesis_evaluation is not None
        assert result.state.synthesis_evaluation.reasoning == "All policy criteria satisfied."
