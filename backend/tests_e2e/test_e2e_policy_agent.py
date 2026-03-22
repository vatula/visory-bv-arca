"""Phase 7 E2E — Policy Extraction Agent prompt evaluation tests.

These tests call the real BedrockConverseModel via the
``policy_extraction_agent`` fixture.  NO mocking is applied (PLAN_OVERRIDE §7).

Validation focus:
  - ``PolicyRuleContainer`` schema is always returned (Pydantic validation).
  - Travel policy: at least one blocking rule references Airbnb / non-standard
    peer-to-peer lodging, because the travel.md policy document explicitly
    prohibits it.
  - Cloud FinOps policy: at least one rule captures the $500 AUD threshold and
    names a project code or cost centre as a required field.

Per PLAN_OVERRIDE §7 iterative prompt tuning rule: if any assertion fails,
adjust the Agent system_prompt in ``src/services/bedrock.py`` and re-run
this suite until extraction is reliable.  Do NOT change Python logic first.
"""
from __future__ import annotations

import structlog
from pydantic_ai import Agent

from src.graph.state import PolicyRule, PolicyRuleContainer
from tests_e2e.helpers import load_policy_content

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Test 1 — Travel policy: Airbnb blocking rule must be extracted
# ---------------------------------------------------------------------------


async def test_travel_policy_extracts_airbnb_blocking_rule(
    policy_extraction_agent: Agent[None, PolicyRuleContainer],
    travel_policy_content: str,
) -> None:
    """travel.md must yield at least one blocking rule that references Airbnb.

    Section 3 of the travel policy explicitly prohibits peer-to-peer lodging
    networks (Airbnb, Stayz, Booking.com).  Section 4 mandates a Line Manager
    exception approval before the expense can be cleared.  The agent must
    extract this as an is_blocking=True rule mentioning the non-standard
    provider.
    """
    prompt = (
        f"Extract all actionable compliance rules from the following corporate "
        f"policy document:\n\n{travel_policy_content}"
    )

    result = await policy_extraction_agent.run(prompt)
    output: PolicyRuleContainer = result.output

    logger.info(
        "e2e_policy_extraction_result",
        policy="travel.md",
        rule_count=len(output.rules),
        rules=[r.model_dump() for r in output.rules],
    )

    assert isinstance(output, PolicyRuleContainer)
    assert len(output.rules) >= 1, "Expected at least one rule to be extracted from travel.md"

    # Every extracted rule must satisfy the PolicyRule schema
    for rule in output.rules:
        assert isinstance(rule, PolicyRule)
        assert rule.category, "Every rule must have a non-empty category"
        assert rule.description, "Every rule must have a non-empty description"

    # At least one rule must be blocking and reference Airbnb / peer-to-peer lodging
    blocking_rules = [r for r in output.rules if r.is_blocking]
    assert blocking_rules, (
        f"Expected at least one is_blocking=True rule in travel policy. "
        f"Got rules: {[r.description for r in output.rules]}"
    )

    airbnb_rule_found = any(
        any(kw in r.description.lower() for kw in ("airbnb", "peer-to-peer", "non-standard", "short-term rental"))
        for r in blocking_rules
    )
    assert airbnb_rule_found, (
        f"Expected a blocking rule mentioning Airbnb / non-standard lodging. "
        f"Blocking rule descriptions: {[r.description for r in blocking_rules]}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Cloud FinOps policy: $500 threshold and project code required field
# ---------------------------------------------------------------------------


async def test_cloud_finops_policy_extracts_threshold_and_required_fields(
    policy_extraction_agent: Agent[None, PolicyRuleContainer],
    cloud_policy_content: str,
) -> None:
    """cloud_and_finops_allocation.md must yield a rule with threshold_amount=500.

    Section 3 of the cloud FinOps policy states that cloud charges exceeding
    $500 AUD per transaction trigger mandatory FinOps review.  Section 4
    mandates a Project Code or Cost Center as required fields.  The agent must
    extract both the monetary threshold and the required field names.
    """
    prompt = (
        f"Extract all actionable compliance rules from the following corporate "
        f"policy document:\n\n{cloud_policy_content}"
    )

    result = await policy_extraction_agent.run(prompt)
    output: PolicyRuleContainer = result.output

    logger.info(
        "e2e_policy_extraction_result",
        policy="cloud_and_finops_allocation.md",
        rule_count=len(output.rules),
        rules=[r.model_dump() for r in output.rules],
    )

    assert isinstance(output, PolicyRuleContainer)
    assert len(output.rules) >= 1, (
        "Expected at least one rule to be extracted from cloud_and_finops_allocation.md"
    )

    # Every extracted rule must satisfy the PolicyRule schema
    for rule in output.rules:
        assert isinstance(rule, PolicyRule)
        assert rule.category, "Every rule must have a non-empty category"
        assert rule.description, "Every rule must have a non-empty description"

    # At least one rule must capture the $500 threshold
    threshold_rules = [r for r in output.rules if r.threshold_amount is not None]
    assert threshold_rules, (
        f"Expected at least one rule with a threshold_amount. "
        f"Got rules: {[r.description for r in output.rules]}"
    )

    threshold_values = [r.threshold_amount for r in threshold_rules]
    assert 500.0 in threshold_values, (
        f"Expected threshold_amount=500.0 to be extracted from the cloud policy. "
        f"Got threshold values: {threshold_values}"
    )

    # At least one rule must list project code / cost center as a required field
    all_required: list[str] = [
        field.lower()
        for rule in output.rules
        for field in rule.required_fields
    ]
    project_code_present = any(
        any(kw in field for kw in ("project", "cost", "code", "center", "centre"))
        for field in all_required
    )
    assert project_code_present, (
        f"Expected 'project_code' or 'cost_center' in required_fields of at least one rule. "
        f"Got all required_fields: {all_required}"
    )
