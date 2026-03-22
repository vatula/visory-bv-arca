"""Phase 7 E2E — Synthesis Agent prompt evaluation tests.

These tests call the real BedrockConverseModel via the ``synthesis_agent``
fixture.  NO mocking is applied (PLAN_OVERRIDE §7).

Validation focus:
  - ``SynthesisEvaluation`` schema is always returned (Pydantic validation).
  - When given a fully evidenced context (transaction + policy + vagueness
    summary), the agent returns a well-formed confidence score in [0.0, 1.0]
    with a non-empty reasoning string.
  - When given an under-evidenced context (vague transaction, no supporting
    evidence, policy flags present), the agent surfaces identifiable risks in
    the ``key_risks`` list, signalling that the system should escalate rather
    than auto-approve.

Per PLAN_OVERRIDE §7 iterative prompt tuning rule: if any assertion fails,
adjust the Agent system_prompt in ``src/services/bedrock.py`` and re-run
this suite until extraction is reliable.  Do NOT change Python logic first.
"""
from __future__ import annotations

from typing import Any

import structlog
from pydantic_ai import Agent

from src.graph.state import SynthesisEvaluation
from tests_e2e.helpers import find_transaction, load_policy_content

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers — build realistic merged-context strings from resource fixtures
# ---------------------------------------------------------------------------


def _build_full_context(all_transactions: list[dict[str, Any]]) -> str:
    """Build a complete merged context for tx_100042 QANTAS AIRWAYS -450.0 AUD.

    This is a standard airline booking that passes the travel policy (approved
    channel, standard carrier, amount below blocking thresholds).  It should
    yield a relatively high confidence score.
    """
    tx = find_transaction(all_transactions, "tx_100042")
    travel_policy = load_policy_content("travel.md")
    return (
        f"TRANSACTION\n"
        f"  ID: {tx.transaction_id}\n"
        f"  Date: {tx.date}\n"
        f"  Description: {tx.description}\n"
        f"  Amount: {tx.amount} {tx.currency}\n"
        f"  Type: {tx.type}\n\n"
        f"VAGUENESS ANALYSIS\n"
        f"  is_vague: false\n"
        f"  missing_context: none — standard airline booking on approved carrier\n"
        f"  extracted_entities: {{vendor: 'Qantas Airways', booking_type: 'flight'}}\n\n"
        f"RELEVANT POLICY EXCERPT\n"
        f"{travel_policy}\n\n"
        f"EVIDENCE DOCUMENTS\n"
        f"  - resources/invoices/acc_1001_1.md (itinerary confirmed)\n\n"
        f"Assess overall compliance confidence for posting to the Xero ledger."
    )


def _build_vague_context(all_transactions: list[dict[str, Any]]) -> str:
    """Build an under-evidenced context for tx_100043 AIRBNB -680.0 AUD.

    Airbnb is a prohibited non-standard lodging provider.  No manager approval
    note is present, no evidence document was found, and the vagueness agent
    flagged the transaction.  The synthesis agent should identify significant
    risks and return a lower confidence score.
    """
    tx = find_transaction(all_transactions, "tx_100043")
    travel_policy = load_policy_content("travel.md")
    return (
        f"TRANSACTION\n"
        f"  ID: {tx.transaction_id}\n"
        f"  Date: {tx.date}\n"
        f"  Description: {tx.description}\n"
        f"  Amount: {tx.amount} {tx.currency}\n"
        f"  Type: {tx.type}\n\n"
        f"VAGUENESS ANALYSIS\n"
        f"  is_vague: true\n"
        f"  missing_context: No Line Manager exception approval note found. "
        f"Airbnb is a prohibited peer-to-peer lodging provider per travel policy.\n"
        f"  extracted_entities: {{vendor: 'Airbnb', provider_type: 'non-standard lodging'}}\n\n"
        f"RELEVANT POLICY EXCERPT\n"
        f"{travel_policy}\n\n"
        f"EVIDENCE DOCUMENTS\n"
        f"  (none retrieved)\n\n"
        f"Assess overall compliance confidence for posting to the Xero ledger."
    )


# ---------------------------------------------------------------------------
# Test 1 — Full context: valid confidence score and non-empty reasoning
# ---------------------------------------------------------------------------


async def test_synthesis_with_complete_context_returns_valid_score(
    synthesis_agent: Agent[None, SynthesisEvaluation],
    all_transactions: list[dict[str, Any]],
) -> None:
    """A fully evidenced Qantas tx must produce a well-formed SynthesisEvaluation.

    The agent must return:
      - confidence_score strictly within [0.0, 1.0] (enforced by Pydantic Field)
      - a non-empty reasoning string explaining the assessment
      - a list of key_risks (may be empty for a clean transaction)
    """
    context = _build_full_context(all_transactions)

    result = await synthesis_agent.run(context)
    output: SynthesisEvaluation = result.output

    logger.info(
        "e2e_synthesis_result",
        scenario="full_context_qantas",
        confidence_score=output.confidence_score,
        reasoning_length=len(output.reasoning),
        key_risks=output.key_risks,
    )

    assert isinstance(output, SynthesisEvaluation)
    assert 0.0 <= output.confidence_score <= 1.0, (
        f"confidence_score must be in [0.0, 1.0], got: {output.confidence_score}"
    )
    assert output.reasoning.strip(), "reasoning must be a non-empty string"
    assert isinstance(output.key_risks, list), "key_risks must be a list"


# ---------------------------------------------------------------------------
# Test 2 — Vague context: agent must identify risks for blocked Airbnb tx
# ---------------------------------------------------------------------------


async def test_synthesis_with_vague_context_identifies_risks(
    synthesis_agent: Agent[None, SynthesisEvaluation],
    all_transactions: list[dict[str, Any]],
) -> None:
    """An Airbnb tx with no approval evidence must surface identifiable risks.

    The vague context explicitly tells the agent the transaction is flagged
    as vague, the provider is prohibited, and no evidence was retrieved.
    The agent must:
      - return a well-formed SynthesisEvaluation (schema check)
      - populate key_risks with at least one entry describing the compliance gap
      - return a confidence_score < 1.0 (not full confidence for a flagged tx)
    """
    context = _build_vague_context(all_transactions)

    result = await synthesis_agent.run(context)
    output: SynthesisEvaluation = result.output

    logger.info(
        "e2e_synthesis_result",
        scenario="vague_context_airbnb",
        confidence_score=output.confidence_score,
        reasoning_length=len(output.reasoning),
        key_risks=output.key_risks,
    )

    assert isinstance(output, SynthesisEvaluation)
    assert 0.0 <= output.confidence_score <= 1.0, (
        f"confidence_score must be in [0.0, 1.0], got: {output.confidence_score}"
    )
    assert output.confidence_score < 1.0, (
        f"Expected confidence_score < 1.0 for a flagged Airbnb transaction, "
        f"got: {output.confidence_score}"
    )
    assert output.reasoning.strip(), "reasoning must be a non-empty string"
    assert len(output.key_risks) >= 1, (
        f"Expected at least one key_risk for the Airbnb vague context. "
        f"Got: {output.key_risks}"
    )

    all_risks_text = " ".join(output.key_risks).lower()
    assert any(
        kw in all_risks_text
        for kw in ("airbnb", "approval", "non-standard", "prohibited", "policy", "missing", "lodging")
    ), (
        f"Expected key_risks to reference the Airbnb / approval gap. "
        f"Got: {output.key_risks}"
    )
