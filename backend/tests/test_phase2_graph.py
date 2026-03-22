"""Phase 2 tests: AnomalyGraph + PolicyGraph.

Bedrock agents are mocked via unittest.mock.AsyncMock so no AWS credentials
are required.  All transaction fixtures are loaded directly from
resources/xero_api_feed.json (AGENTS.md §4 — no dummy dicts).
"""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from src.graph.anomaly import ExtractLedgerVarianceNode
from src.graph.graphs import anomaly_graph, policy_graph
from src.graph.policy import QueryNotionNode
from src.graph.state import (
    AnomalyVaguenessResult,
    ArcraState,
    PolicyRule,
    PolicyRuleContainer,
    SynthesisEvaluation,
    XeroTransaction,
)
from src.services.bedrock import ArcraDeps

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_XERO_FEED_PATH = os.path.join(_REPO_ROOT, "resources", "xero_api_feed.json")
_RESOURCES_PATH = os.path.join(_REPO_ROOT, "resources")


def _load_transactions() -> list[dict[str, Any]]:
    with open(_XERO_FEED_PATH) as fh:
        data: list[dict[str, Any]] = json.load(fh)
    txs: list[dict[str, Any]] = []
    for account in data:
        txs.extend(account["transactions"])
    return txs


def _find_tx(txs: list[dict[str, Any]], tx_id: str) -> dict[str, Any]:
    for tx in txs:
        if tx["transaction_id"] == tx_id:
            return tx
    raise KeyError(f"Transaction {tx_id!r} not found in feed")


def _make_state(tx_dict: dict[str, Any]) -> ArcraState:
    tx = XeroTransaction(
        transaction_id=tx_dict["transaction_id"],
        date=tx_dict["date"],
        description=tx_dict["description"],
        amount=tx_dict["amount"],
        currency=tx_dict["currency"],
        type=tx_dict["type"],
    )
    return ArcraState(transaction=tx)


def _mock_vagueness_agent(is_vague: bool = True, missing: str = "project code") -> Any:
    result = MagicMock()
    result.output = AnomalyVaguenessResult(
        is_vague=is_vague,
        missing_context=missing,
        extracted_entities={},
    )
    mock = AsyncMock()
    mock.run = AsyncMock(return_value=result)
    return mock


def _mock_policy_agent(rules: list[PolicyRule] | None = None) -> Any:
    result = MagicMock()
    result.output = PolicyRuleContainer(rules=rules or [
        PolicyRule(
            category="cloud",
            description="Cloud spend >$500 requires project code",
            threshold_amount=500.0,
            required_fields=["project_code"],
            is_blocking=True,
        )
    ])
    mock = AsyncMock()
    mock.run = AsyncMock(return_value=result)
    return mock


def _mock_synthesis_agent() -> Any:
    return Agent(TestModel(), output_type=SynthesisEvaluation)


def _make_deps(
    vagueness_agent: Any | None = None,
    policy_agent: Any | None = None,
    synthesis_agent: Any | None = None,
) -> ArcraDeps:
    return ArcraDeps(
        db_path=":memory:",
        resources_path=_RESOURCES_PATH,
        vagueness_agent=vagueness_agent or _mock_vagueness_agent(),
        policy_extraction_agent=policy_agent or _mock_policy_agent(),
        synthesis_agent=synthesis_agent or _mock_synthesis_agent(),
        confidence_threshold=0.75,
    )


# ---------------------------------------------------------------------------
# ArcraState computed_field tests (pure Python — no I/O)
# ---------------------------------------------------------------------------

class TestArcraStateThresholds:
    """PLAN_OVERRIDE #1: all threshold math must live in @computed_field."""

    def setup_method(self) -> None:
        self.txs = _load_transactions()

    def test_cloud_above_threshold_flagged(self) -> None:
        """tx_100008 GOOGLE CLOUD -890.10 > $500 → requires_policy_check=True."""
        state = _make_state(_find_tx(self.txs, "tx_100008"))
        assert state.requires_policy_check is True
        assert state.policy_category == "cloud"

    def test_cloud_below_threshold_not_flagged(self) -> None:
        """tx_998877 AWS -150.50 ≤ $500 → requires_policy_check=False."""
        state = _make_state(_find_tx(self.txs, "tx_998877"))
        assert state.requires_policy_check is False

    def test_it_asset_above_threshold_flagged(self) -> None:
        """tx_100048 APPLE STORE -2499.00 > $1000 → requires_policy_check=True."""
        state = _make_state(_find_tx(self.txs, "tx_100048"))
        assert state.requires_policy_check is True
        assert state.policy_category == "it_asset"

    def test_it_asset_below_threshold_not_flagged(self) -> None:
        """tx_100049 JB HI FI -150.00 ≤ $1000 → requires_policy_check=False."""
        state = _make_state(_find_tx(self.txs, "tx_100049"))
        assert state.requires_policy_check is False

    def test_airbnb_always_flagged_regardless_of_amount(self) -> None:
        """tx_100043 AIRBNB -680.00 → requires_policy_check=True (categorical block)."""
        state = _make_state(_find_tx(self.txs, "tx_100043"))
        assert state.requires_policy_check is True
        assert state.policy_category == "travel"

    def test_tax_above_threshold_flagged(self) -> None:
        """tx_100025 ATO PAYG INSTALMENT -3500.00 > $1000 → True."""
        state = _make_state(_find_tx(self.txs, "tx_100025"))
        assert state.requires_policy_check is True
        assert state.policy_category == "tax"

    def test_normal_saas_subscription_not_flagged(self) -> None:
        """tx_100037 ATLASSIAN -135.00 → not an anomaly (below cloud threshold)."""
        state = _make_state(_find_tx(self.txs, "tx_100037"))
        assert state.requires_policy_check is False

    def test_income_credit_not_flagged(self) -> None:
        """tx_100002 STRIPE PAYMENTS +4200.00 (credit) → not an anomaly."""
        state = _make_state(_find_tx(self.txs, "tx_100002"))
        assert state.requires_policy_check is False

    def test_entertainment_at_threshold_flagged(self) -> None:
        """tx_100045 CAFE SYDNEY -120.00 ≥ $100 → requires_policy_check=True."""
        state = _make_state(_find_tx(self.txs, "tx_100045"))
        assert state.requires_policy_check is True
        assert state.policy_category == "entertainment"

    def test_policy_category_none_for_unmatched(self) -> None:
        """tx_100050 FEDEX SHIPPING → no keyword match → policy_category=None."""
        state = _make_state(_find_tx(self.txs, "tx_100050"))
        assert state.policy_category is None
        assert state.requires_policy_check is False


# ---------------------------------------------------------------------------
# AnomalyGraph integration tests
# ---------------------------------------------------------------------------

class TestAnomalyGraph:
    @pytest.mark.asyncio
    async def test_normal_transaction_ends_without_llm_call(self) -> None:
        """tx_998877 AWS -150.50: below threshold → End(None), no LLM call."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_998877"))
        mock_agent = _mock_vagueness_agent()
        deps = _make_deps(vagueness_agent=mock_agent)
        result = await anomaly_graph.run(
            ExtractLedgerVarianceNode(), state=state, deps=deps
        )
        assert result.state.status == "normal"
        assert result.state.anomaly_detected is False
        mock_agent.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_cloud_anomaly_calls_llm_and_sets_flag(self) -> None:
        """tx_100008 GOOGLE CLOUD -890.10: above threshold → LLM called, anomaly_detected=True."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_100008"))
        mock_agent = _mock_vagueness_agent(is_vague=True, missing="project code")
        deps = _make_deps(vagueness_agent=mock_agent)
        result = await anomaly_graph.run(
            ExtractLedgerVarianceNode(), state=state, deps=deps
        )
        assert result.state.anomaly_detected is True
        assert result.state.status == "anomaly_detected"
        assert result.state.vagueness_result is not None
        assert result.state.vagueness_result.is_vague is True
        mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_airbnb_anomaly_detected(self) -> None:
        """tx_100043 AIRBNB: categorical block → anomaly_detected=True."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_100043"))
        deps = _make_deps()
        result = await anomaly_graph.run(
            ExtractLedgerVarianceNode(), state=state, deps=deps
        )
        assert result.state.anomaly_detected is True
        assert result.state.policy_category == "travel"

    @pytest.mark.asyncio
    async def test_it_asset_apple_store_anomaly(self) -> None:
        """tx_100048 APPLE STORE -2499.00: >$1000 IT asset → anomaly_detected=True."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_100048"))
        deps = _make_deps()
        result = await anomaly_graph.run(
            ExtractLedgerVarianceNode(), state=state, deps=deps
        )
        assert result.state.anomaly_detected is True
        assert result.state.policy_category == "it_asset"

    @pytest.mark.asyncio
    async def test_tax_ato_payg_anomaly(self) -> None:
        """tx_100025 ATO PAYG INSTALMENT -3500.00: >$1000 → anomaly_detected=True."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_100025"))
        deps = _make_deps()
        result = await anomaly_graph.run(
            ExtractLedgerVarianceNode(), state=state, deps=deps
        )
        assert result.state.anomaly_detected is True
        assert result.state.policy_category == "tax"


# ---------------------------------------------------------------------------
# PolicyGraph integration tests
# ---------------------------------------------------------------------------

class TestPolicyGraph:
    @pytest.mark.asyncio
    async def test_cloud_policy_loaded_and_rules_extracted(self) -> None:
        """Cloud anomaly state → QueryNotionNode loads cloud policy → rules extracted."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_100008"))
        state.anomaly_detected = True
        state.status = "anomaly_detected"
        rules = [
            PolicyRule(
                category="cloud",
                description="Charges >$500 require project code",
                threshold_amount=500.0,
                required_fields=["project_code"],
                is_blocking=True,
            )
        ]
        deps = _make_deps(policy_agent=_mock_policy_agent(rules=rules))
        result = await policy_graph.run(QueryNotionNode(), state=state, deps=deps)
        assert result.state.status == "policy_extracted"
        assert len(result.state.policy_context) == 1
        assert result.state.policy_context[0].category == "cloud"
        assert result.state.policy_file_path is not None
        assert "cloud_and_finops_allocation" in result.state.policy_file_path

    @pytest.mark.asyncio
    async def test_travel_policy_loaded_for_airbnb(self) -> None:
        """Airbnb anomaly → travel.md policy loaded."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_100043"))
        state.anomaly_detected = True
        state.status = "anomaly_detected"
        deps = _make_deps()
        result = await policy_graph.run(QueryNotionNode(), state=state, deps=deps)
        assert result.state.policy_file_path is not None
        assert "travel" in result.state.policy_file_path

    @pytest.mark.asyncio
    async def test_tax_policy_loaded_for_ato(self) -> None:
        """ATO PAYG anomaly → Tax_Compliance.md policy loaded."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_100025"))
        state.anomaly_detected = True
        state.status = "anomaly_detected"
        deps = _make_deps()
        result = await policy_graph.run(QueryNotionNode(), state=state, deps=deps)
        assert result.state.policy_file_path is not None
        assert "Tax_Compliance" in result.state.policy_file_path

    @pytest.mark.asyncio
    async def test_unmapped_category_escalates(self) -> None:
        """Transaction with no keyword match → EscalateNode → status=escalated."""
        txs = _load_transactions()
        # FEDEX SHIPPING has no policy category
        state = _make_state(_find_tx(txs, "tx_100050"))
        # Force anomaly_detected to simulate a hypothetical escalation path
        state.anomaly_detected = True
        state.status = "anomaly_detected"
        deps = _make_deps()
        result = await policy_graph.run(QueryNotionNode(), state=state, deps=deps)
        assert result.state.status == "escalated"
        assert result.state.error_message is not None

    @pytest.mark.asyncio
    async def test_policy_extraction_failure_escalates(self) -> None:
        """If the Bedrock policy agent raises, ExtractRulesNode escalates cleanly."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_100008"))
        state.anomaly_detected = True
        state.status = "anomaly_detected"
        failing_agent = AsyncMock()
        failing_agent.run = AsyncMock(side_effect=RuntimeError("Bedrock timeout"))
        deps = _make_deps(policy_agent=failing_agent)
        result = await policy_graph.run(QueryNotionNode(), state=state, deps=deps)
        assert result.state.status == "escalated"
        assert "Bedrock timeout" in (result.state.error_message or "")

    @pytest.mark.asyncio
    async def test_full_pipeline_cloud_anomaly_end_to_end(self) -> None:
        """End-to-end: AnomalyGraph detects cloud anomaly → PolicyGraph extracts rules."""
        txs = _load_transactions()
        state = _make_state(_find_tx(txs, "tx_100001"))  # AWS EMEA -450.25 (below 500)
        # Use tx_100008 GOOGLE CLOUD -890.10 for a proper above-threshold cloud tx
        state = _make_state(_find_tx(txs, "tx_100008"))
        mock_vagueness = _mock_vagueness_agent(is_vague=True, missing="project code")
        mock_policy = _mock_policy_agent()
        deps = _make_deps(vagueness_agent=mock_vagueness, policy_agent=mock_policy)
        # Phase 1: AnomalyGraph
        anomaly_result = await anomaly_graph.run(
            ExtractLedgerVarianceNode(), state=state, deps=deps
        )
        state = anomaly_result.state
        assert state.anomaly_detected is True
        # Phase 2: PolicyGraph
        policy_result = await policy_graph.run(
            QueryNotionNode(), state=state, deps=deps
        )
        final_state = policy_result.state
        assert final_state.status == "policy_extracted"
        assert len(final_state.policy_context) >= 1
