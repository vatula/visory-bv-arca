from __future__ import annotations

from dataclasses import dataclass

import structlog
from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.settings import ModelSettings

from src.core.config import Settings
from src.graph.state import AnomalyVaguenessResult, PolicyRuleContainer, SynthesisEvaluation

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
    synthesis_agent: Agent[None, SynthesisEvaluation]
    confidence_threshold: float = 0.75


def build_vagueness_agent(settings: Settings) -> Agent[None, AnomalyVaguenessResult]:
    """Factory: returns a Bedrock-backed agent for text-entity extraction only.

    The agent must NOT evaluate monetary thresholds — those are handled by
    ArcraState.requires_policy_check (PLAN_OVERRIDE #1).
    """
    model = BedrockConverseModel(model_name=settings.bedrock_model_id, settings=ModelSettings(temperature=0.0))
    return Agent(
        model,
        output_type=AnomalyVaguenessResult,
        system_prompt=(
            "You are a financial transaction analyst. "
            "Your ONLY job is to extract text entities from transaction descriptions. "
            "You must NOT perform any arithmetic or threshold evaluations — "
            "those are handled by deterministic Python code. "
            "Return is_vague=true if critical identifying context is ABSENT from the description. "
            "IMPORTANT DEFINITIONS — read carefully before deciding:\n"
            "  - A PROJECT CODE or COST CENTER is a distinct alphanumeric identifier "
            "SEPARATE from the vendor name (examples: 'PROJ-123', 'CC-MKTG', 'P9042', "
            "'INFRA-PROD'). The vendor name itself (e.g. 'GOOGLE CLOUD', 'AWS SERVICES', "
            "'AZURE', 'DATADOG') is NOT a project code.\n"
            "  - For cloud provider charges (AWS, GCP, Azure, Datadog, GitHub, etc.), "
            "flag is_vague=true if the description contains ONLY the vendor name with no "
            "separate project/cost-center code alongside it.\n"
            "  - For meal/entertainment expenses, flag is_vague=true if no attendee names "
            "or business purpose are present.\n"
            "  - For hardware purchases, flag is_vague=true if no asset tag is present.\n"
            "Populate extracted_entities with any real identifiers you find (NOT vendor names)."
        ),
    )


def build_policy_extraction_agent(
    settings: Settings,
) -> Agent[None, PolicyRuleContainer]:
    """Factory: returns a Bedrock-backed agent for structured rule extraction.

    The agent must NOT invent rules not present in the document (PLAN_OVERRIDE #1).
    """
    model = BedrockConverseModel(model_name=settings.bedrock_model_id, settings=ModelSettings(temperature=0.0))
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


def build_synthesis_agent(settings: Settings) -> Agent[None, SynthesisEvaluation]:
    """Factory: returns a Bedrock-backed agent for final confidence assessment.

    The agent synthesises the merged context (transaction + policy + evidence)
    and returns a structured confidence score with reasoning.  It must NOT
    re-evaluate monetary thresholds — those are handled by ArcraState computed
    fields (PLAN_OVERRIDE #1).
    """
    model = BedrockConverseModel(model_name=settings.bedrock_model_id, settings=ModelSettings(temperature=0.0))
    return Agent(
        model,
        output_type=SynthesisEvaluation,
        system_prompt=(
            "You are a senior financial compliance officer performing a final review. "
            "You will receive a merged context containing a transaction description, "
            "vagueness analysis, relevant policy rules, and evidence documents. "
            "Your ONLY job is to assess the overall confidence that this transaction "
            "complies with company policy and can be safely posted to the Xero ledger. "
            "Return a confidence_score between 0.0 (no confidence) and 1.0 (full "
            "confidence), a human-readable reasoning string, and a list of key_risks "
            "identified. Do NOT perform arithmetic on amounts — that has already been done."
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
        synthesis_agent=build_synthesis_agent(settings),
        confidence_threshold=settings.confidence_threshold,
    )
