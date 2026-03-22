"""Phase 7 E2E — Vagueness Agent prompt evaluation tests.

These tests call the real BedrockConverseModel via the ``vagueness_agent``
fixture.  NO mocking is applied (PLAN_OVERRIDE §7).

Validation focus:
  - ``AnomalyVaguenessResult`` schema is always returned (Pydantic validation).
  - ``is_vague`` is correctly set to True for transactions with missing
    critical context (cloud charges without a project code, Airbnb lodging
    without a manager approval note, entertainment without attendees).
  - ``extracted_entities`` surfaces the key vendor / provider name so
    downstream nodes can reference it in audit telemetry.

Per PLAN_OVERRIDE §7 iterative prompt tuning rule: if any assertion fails,
adjust the Agent system_prompt in ``src/services/bedrock.py`` and re-run
this suite until extraction is reliable.  Do NOT change Python logic first.
"""
from __future__ import annotations

from typing import Any

import structlog
from pydantic_ai import Agent

from src.graph.state import AnomalyVaguenessResult
from tests_e2e.helpers import build_transaction_prompt, find_transaction

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Test 1 — Airbnb: non-standard lodging provider must be flagged as vague
# ---------------------------------------------------------------------------


async def test_airbnb_non_standard_provider_flagged_as_vague(
    vagueness_agent: Agent[None, AnomalyVaguenessResult],
    all_transactions: list[dict[str, Any]],
) -> None:
    """tx_100043 AIRBNB -680.0 AUD must be flagged is_vague=True.

    The travel policy prohibits peer-to-peer lodging without a recorded Line
    Manager exception approval.  The raw bank-feed description contains no
    such approval reference, so the agent must report missing context and
    surface 'airbnb' as an extracted entity (PLAN_OVERRIDE §7 example).
    """
    tx = find_transaction(all_transactions, "tx_100043")
    prompt = build_transaction_prompt(tx)

    result = await vagueness_agent.run(prompt)
    output: AnomalyVaguenessResult = result.output

    logger.info(
        "e2e_vagueness_result",
        tx_id=tx.transaction_id,
        is_vague=output.is_vague,
        missing_context=output.missing_context,
        extracted_entities=output.extracted_entities,
    )

    assert isinstance(output, AnomalyVaguenessResult)
    assert output.is_vague is True, (
        f"Expected Airbnb tx_100043 to be flagged as vague. "
        f"missing_context='{output.missing_context}'"
    )
    assert output.missing_context, "missing_context must be a non-empty string"

    all_text = " ".join(
        list(output.extracted_entities.keys()) + list(output.extracted_entities.values())
    ).lower()
    assert "airbnb" in all_text, (
        f"Expected 'airbnb' to appear in extracted_entities, got: {output.extracted_entities}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Google Cloud: cloud charge over $500 with no project code
# ---------------------------------------------------------------------------


async def test_google_cloud_without_project_code_flagged_as_vague(
    vagueness_agent: Agent[None, AnomalyVaguenessResult],
    all_transactions: list[dict[str, Any]],
) -> None:
    """tx_100008 GOOGLE CLOUD -890.1 AUD must be flagged is_vague=True.

    The cloud FinOps policy mandates a Project Code or Cost Center for any
    individual cloud provider charge exceeding $500 AUD.  The bank-feed
    description is bare — no project code present — so the agent must detect
    the missing entity and flag the transaction as vague.
    """
    tx = find_transaction(all_transactions, "tx_100008")
    prompt = build_transaction_prompt(tx)

    result = await vagueness_agent.run(prompt)
    output: AnomalyVaguenessResult = result.output

    logger.info(
        "e2e_vagueness_result",
        tx_id=tx.transaction_id,
        is_vague=output.is_vague,
        missing_context=output.missing_context,
        extracted_entities=output.extracted_entities,
    )

    assert isinstance(output, AnomalyVaguenessResult)
    assert output.is_vague is True, (
        f"Expected GOOGLE CLOUD tx_100008 to be flagged as vague (no project code). "
        f"missing_context='{output.missing_context}'"
    )
    assert output.missing_context, "missing_context must be a non-empty string"

    missing_lower = output.missing_context.lower()
    assert any(kw in missing_lower for kw in ("project", "cost center", "code", "allocation")), (
        f"Expected missing_context to reference a project code or cost center, "
        f"got: '{output.missing_context}'"
    )


# ---------------------------------------------------------------------------
# Test 3 — Cafe Sydney: entertainment ≥ $100 with no attendee list
# ---------------------------------------------------------------------------


async def test_entertainment_without_attendees_flagged_as_vague(
    vagueness_agent: Agent[None, AnomalyVaguenessResult],
    all_transactions: list[dict[str, Any]],
) -> None:
    """tx_100045 CAFE SYDNEY -120.0 AUD must be flagged is_vague=True.

    The client entertainment policy requires a full attendee list for any
    dining expense equal to or above $100 AUD (FBT substantiation).  The
    bank-feed entry contains no attendee information, so the agent must flag
    the transaction as vague with missing attendee context.
    """
    tx = find_transaction(all_transactions, "tx_100045")
    prompt = build_transaction_prompt(tx)

    result = await vagueness_agent.run(prompt)
    output: AnomalyVaguenessResult = result.output

    logger.info(
        "e2e_vagueness_result",
        tx_id=tx.transaction_id,
        is_vague=output.is_vague,
        missing_context=output.missing_context,
        extracted_entities=output.extracted_entities,
    )

    assert isinstance(output, AnomalyVaguenessResult)
    assert output.is_vague is True, (
        f"Expected CAFE SYDNEY tx_100045 to be flagged as vague (no attendees). "
        f"missing_context='{output.missing_context}'"
    )
    assert output.missing_context, "missing_context must be a non-empty string"

    missing_lower = output.missing_context.lower()
    assert any(kw in missing_lower for kw in ("attendee", "guest", "participant", "client", "fbt")), (
        f"Expected missing_context to reference attendees or FBT substantiation, "
        f"got: '{output.missing_context}'"
    )
