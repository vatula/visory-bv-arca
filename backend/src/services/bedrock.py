from __future__ import annotations

from dataclasses import dataclass

import structlog
from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel

from src.core.config import Settings
from src.graph.state import AnomalyVaguenessResult, PolicyRuleContainer

logger = structlog.get_logger(__name__)


@dataclass
class ArcraDeps:
    """Formal dependency model for FSM execution context.

    Uses a dataclass (not BaseModel) because it holds non-serialisable
    pydantic_ai Agent instances.  Injected into pydantic_graph nodes strictly
    via ``ctx: GraphRunContext[ArcraState, ArcraDeps]`` — never via __init__
    or global state (AGENTS.md FSM Anti-Patterns).
    """

    db_path: str
    resources_path: str
    vagueness_agent: Agent[None, AnomalyVaguenessResult]
    policy_extraction_agent: Agent[None, PolicyRuleContainer]


def build_vagueness_agent(settings: Settings) -> Agent[None, AnomalyVaguenessResult]:
    """Factory: returns a Bedrock-backed agent for text-entity extraction only.

    The agent must NOT evaluate monetary thresholds — those are handled by
    ArcraState.requires_policy_check (PLAN_OVERRIDE #1).
    """
    model = BedrockConverseModel(model_name=settings.bedrock_model_id)
    return Agent(
        model,
        output_type=AnomalyVaguenessResult,
        system_prompt=(
            "You are a financial transaction analyst. "
            "Your ONLY job is to extract text entities from transaction descriptions. "
            "You must NOT perform any arithmetic or threshold evaluations — "
            "those are handled by deterministic Python code. "
            "Return is_vague=true if critical identifying context is absent "
            "(e.g. no project code for a cloud charge, no attendees for a meal "
            "expense, no asset tag for hardware, no ATO reference for a tax payment). "
            "Populate extracted_entities with any identifiers you find."
        ),
    )


def build_policy_extraction_agent(
    settings: Settings,
) -> Agent[None, PolicyRuleContainer]:
    """Factory: returns a Bedrock-backed agent for structured rule extraction.

    The agent must NOT invent rules not present in the document (PLAN_OVERRIDE #1).
    """
    model = BedrockConverseModel(model_name=settings.bedrock_model_id)
    return Agent(
        model,
        output_type=PolicyRuleContainer,
        system_prompt=(
            "You are a compliance officer reviewing corporate policy documents. "
            "Given a policy document excerpt, extract the actionable rules as "
            "structured JSON inside a 'rules' array. "
            "For each rule include: category, description, threshold_amount (if stated), "
            "required_fields (list of strings), and is_blocking (bool). "
            "Do NOT invent rules not present in the document."
        ),
    )


def build_deps_from_settings(settings: Settings, resources_path: str) -> ArcraDeps:
    """Build the full ArcraDeps injection container from application settings."""
    logger.info(
        "building_arcra_deps",
        bedrock_model_id=settings.bedrock_model_id,
        resources_path=resources_path,
    )
    return ArcraDeps(
        db_path=settings.database_url,
        resources_path=resources_path,
        vagueness_agent=build_vagueness_agent(settings),
        policy_extraction_agent=build_policy_extraction_agent(settings),
    )
