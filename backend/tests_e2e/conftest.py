"""Shared pytest fixtures for Phase 7 E2E prompt evaluation tests.

All fixtures are session-scoped to avoid rebuilding Bedrock agent objects on
every test.  The ``require_aws_credentials`` autouse fixture short-circuits
the entire session if AWS credentials are absent, providing a clear skip
message rather than an opaque Bedrock authentication error.

Per PLAN_OVERRIDE §7 — the LLM is NOT mocked.  These tests hit the real
BedrockConverseModel endpoint and require valid AWS credentials in the
environment or a local .env file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import structlog
from dotenv import load_dotenv
from pydantic_ai import Agent

from src.core.config import Settings

# Load the project-root .env before Settings is instantiated so credentials
# are available regardless of the working directory the test runner uses.
load_dotenv(Path(__file__).parents[2] / ".env", override=False)

from src.graph.state import AnomalyVaguenessResult, PolicyRuleContainer, SynthesisEvaluation
from src.services.bedrock import (
    build_policy_extraction_agent,
    build_synthesis_agent,
    build_vagueness_agent,
)
from tests_e2e.helpers import load_all_transactions, load_policy_content

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration & credential guard
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Load application settings from environment / .env file."""
    return Settings()


@pytest.fixture(scope="session", autouse=True)
def require_aws_credentials(settings: Settings) -> None:
    """Skip the entire e2e session when AWS credentials are not configured.

    This prevents confusing Bedrock authentication errors and makes the
    skip reason explicit in the pytest output.
    """
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        pytest.skip(
            "AWS credentials not configured — set AWS_ACCESS_KEY_ID and "
            "AWS_SECRET_ACCESS_KEY (or populate .env) to run e2e LLM tests."
        )


# ---------------------------------------------------------------------------
# Transaction data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def all_transactions() -> list[dict[str, Any]]:
    """Return all flattened transactions from resources/xero_api_feed.json.

    Per AGENTS.md §4 — real fixture data only, no dummy dicts.
    """
    return load_all_transactions()


# ---------------------------------------------------------------------------
# Policy content fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def travel_policy_content() -> str:
    """Raw markdown text of the corporate travel policy."""
    return load_policy_content("travel.md")


@pytest.fixture(scope="session")
def cloud_policy_content() -> str:
    """Raw markdown text of the cloud FinOps allocation policy."""
    return load_policy_content("cloud_and_finops_allocation.md")


@pytest.fixture(scope="session")
def entertainment_policy_content() -> str:
    """Raw markdown text of the client entertainment policy."""
    return load_policy_content("client_entertainment.md")


# ---------------------------------------------------------------------------
# LLM agent fixtures — real BedrockConverseModel, no mocking
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def vagueness_agent(settings: Settings) -> Agent[None, AnomalyVaguenessResult]:
    """Real vagueness extraction agent backed by BedrockConverseModel."""
    agent = build_vagueness_agent(settings)
    logger.info(
        "e2e_fixture_ready",
        agent="vagueness_agent",
        model=settings.bedrock_model_id,
    )
    return agent


@pytest.fixture(scope="session")
def policy_extraction_agent(settings: Settings) -> Agent[None, PolicyRuleContainer]:
    """Real policy extraction agent backed by BedrockConverseModel."""
    agent = build_policy_extraction_agent(settings)
    logger.info(
        "e2e_fixture_ready",
        agent="policy_extraction_agent",
        model=settings.bedrock_model_id,
    )
    return agent


@pytest.fixture(scope="session")
def synthesis_agent(settings: Settings) -> Agent[None, SynthesisEvaluation]:
    """Real synthesis confidence agent backed by BedrockConverseModel."""
    agent = build_synthesis_agent(settings)
    logger.info(
        "e2e_fixture_ready",
        agent="synthesis_agent",
        model=settings.bedrock_model_id,
    )
    return agent
