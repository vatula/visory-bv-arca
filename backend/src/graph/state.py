from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

# ---------------------------------------------------------------------------
# Threshold constants — PLAN_OVERRIDE #1: all arithmetic lives here, never
# in the LLM prompt.
# ---------------------------------------------------------------------------
CLOUD_THRESHOLD: float = 500.0
IT_ASSET_THRESHOLD: float = 1000.0
ENTERTAINMENT_THRESHOLD: float = 100.0
TAX_THRESHOLD: float = 1000.0

CLOUD_KEYWORDS: frozenset[str] = frozenset(["aws", "google cloud", "azure", "vultr"])
IT_ASSET_KEYWORDS: frozenset[str] = frozenset(["apple store", "jb hi fi", "jb hi-fi"])
ENTERTAINMENT_KEYWORDS: frozenset[str] = frozenset(
    ["cafe", "uber eats", "deliveroo", "restaurant"]
)
TRAVEL_KEYWORDS: frozenset[str] = frozenset(
    ["airbnb", "qantas", "cabcharge", "uber trip", "virgin australia", "parking"]
)
TAX_KEYWORDS: frozenset[str] = frozenset(["ato payg", "ato", "payg instalment"])

PolicyCategory = Literal["cloud", "it_asset", "entertainment", "travel", "tax"]

# PLAN_OVERRIDE #5: deterministic keyword routing — one-to-one map to policy filenames.
POLICY_FILE_MAP: dict[str, str] = {
    "cloud": "cloud_and_finops_allocation.md",
    "it_asset": "IT_Asset_Procurement.md",
    "entertainment": "client_entertainment.md",
    "travel": "travel.md",
    "tax": "Tax_Compliance.md",
}


class XeroTransaction(BaseModel):
    """Immutable value object representing a single Xero bank-feed transaction."""

    model_config = ConfigDict(frozen=True, strict=True)

    transaction_id: str
    date: str
    description: str
    amount: float
    currency: str
    type: str


class PolicyRule(BaseModel):
    """A structured rule extracted from a corporate policy document by the LLM."""

    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    description: str
    threshold_amount: float | None = None
    required_fields: list[str] = Field(default_factory=list)
    is_blocking: bool = False


class PolicyRuleContainer(BaseModel):
    """Wrapper so pydantic_ai Agent can return a typed list of rules."""

    rules: list[PolicyRule] = Field(default_factory=list)


class AnomalyVaguenessResult(BaseModel):
    """LLM output for vagueness evaluation.

    Per PLAN_OVERRIDE #1, the model ONLY extracts text entities (project codes,
    attendee lists, asset tag IDs, ATO references).  It never evaluates thresholds.
    """

    is_vague: bool
    missing_context: str
    extracted_entities: dict[str, str] = Field(default_factory=dict)


class SynthesisEvaluation(BaseModel):
    """LLM output for the final confidence assessment.

    Per PLAN_OVERRIDE #1, the model only provides a holistic text-based
    confidence judgement — it never re-evaluates monetary thresholds.
    """

    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    key_risks: list[str] = Field(default_factory=list)


class XeroDraft(BaseModel):
    """Simulated Xero ledger draft payload produced by DraftGenerationNode."""

    draft_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: str
    merchant: str
    amount: float
    currency: str
    category: str | None = None
    policy_references: list[str] = Field(default_factory=list)
    evidence_uris: list[str] = Field(default_factory=list)
    confidence_score: float
    reasoning: str
    xero_status: str = "draft"


class ArcraState(BaseModel):
    """Unified mutable state that flows through every ARCRA graph phase.

    @computed_field properties perform all threshold arithmetic so the LLM
    is never asked to do math (PLAN_OVERRIDE #1).
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction: XeroTransaction
    anomaly_detected: bool = False
    vagueness_result: AnomalyVaguenessResult | None = None
    policy_file_path: str | None = None
    policy_context: list[PolicyRule] = Field(default_factory=list)
    evidence_documents: list[str] = Field(default_factory=list)
    slack_thread_ts: str | None = None
    slack_reply: str | None = None
    validation_confidence: float = 0.0
    status: str = "pending"
    error_message: str | None = None
    # Phase 4 — Synthesis
    merged_context: str | None = None
    synthesis_evaluation: SynthesisEvaluation | None = None
    xero_draft: XeroDraft | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def policy_category(self) -> PolicyCategory | None:
        """Deterministically classify the transaction by keyword matching only."""
        desc = self.transaction.description.lower()
        if any(k in desc for k in CLOUD_KEYWORDS):
            return "cloud"
        if any(k in desc for k in IT_ASSET_KEYWORDS):
            return "it_asset"
        if any(k in desc for k in ENTERTAINMENT_KEYWORDS):
            return "entertainment"
        if any(k in desc for k in TRAVEL_KEYWORDS):
            return "travel"
        if any(k in desc for k in TAX_KEYWORDS):
            return "tax"
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def requires_policy_check(self) -> bool:
        """Pure Python threshold gate — PLAN_OVERRIDE #1.

        Returns True when the transaction crosses a policy-defined monetary
        threshold or matches a categorically blocked vendor (e.g. Airbnb).
        The LLM never evaluates these conditions.
        """
        desc = self.transaction.description.lower()
        amount = abs(self.transaction.amount)
        if any(k in desc for k in CLOUD_KEYWORDS) and amount > CLOUD_THRESHOLD:
            return True
        if any(k in desc for k in IT_ASSET_KEYWORDS) and amount > IT_ASSET_THRESHOLD:
            return True
        if (
            any(k in desc for k in ENTERTAINMENT_KEYWORDS)
            and amount >= ENTERTAINMENT_THRESHOLD
        ):
            return True
        if "airbnb" in desc:
            return True
        if any(k in desc for k in TAX_KEYWORDS) and amount > TAX_THRESHOLD:
            return True
        return False
