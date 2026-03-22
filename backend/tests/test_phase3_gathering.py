"""Phase 3 tests — Evidence Gathering FSM.

All tests are hydrated from real project resources:
  - resources/xero_api_feed.json  (live transaction data)
  - resources/invoices/*.md       (invoice corpus)

Bedrock agents are mocked via pydantic_ai TestModel so no AWS calls are made.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.core.db import (
    init_db,
    load_checkpoint,
    load_interrupt,
    load_interrupt_by_slack_ts,
    save_checkpoint,
    save_interrupt,
)
from src.graph.gathering import (
    CheckDriveNode,
    DispatchSlackNode,
    NormalizeToDriveNode,
    SuspendForSlackNode,
    _find_invoice,
    load_state_from_checkpoint,
)
import src.core.config as _config_module
from src.graph.graphs import gathering_graph, resumption_graph
from src.graph.state import AnomalyVaguenessResult, ArcraState, PolicyRuleContainer, XeroTransaction
from src.services.bedrock import ArcraDeps

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RESOURCES_PATH = str(Path(__file__).parents[2] / "resources")
_FEED_PATH = Path(_RESOURCES_PATH) / "xero_api_feed.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point every test at a fresh in-memory-style temp DB."""
    db_file = str(tmp_path / "test_phase3.db")
    monkeypatch.setenv("DATABASE_URL", db_file)
    # Reset the global singleton so get_settings re-reads the new DATABASE_URL
    _config_module._settings = None
    await init_db()


@pytest.fixture()
def xero_transactions() -> list[dict[str, object]]:
    """Load all transactions from the real Xero feed fixture."""
    data: list[dict[str, object]] = json.loads(_FEED_PATH.read_text())
    txns: list[dict[str, object]] = []
    for account in data:
        for tx in account["transactions"]:  # type: ignore[index]
            txns.append(tx)  # type: ignore[arg-type]
    return txns


def _make_tx(**kwargs: object) -> XeroTransaction:
    defaults: dict[str, object] = {
        "transaction_id": "tx_100001",
        "date": "2026-03-17",
        "description": "AWS EMEA",
        "amount": -890.0,
        "currency": "AUD",
        "type": "debit",
    }
    defaults.update(kwargs)
    return XeroTransaction.model_validate(defaults)


def _make_state(**kwargs: object) -> ArcraState:
    tx = kwargs.pop("transaction", _make_tx())
    return ArcraState(transaction=tx, **kwargs)  # type: ignore[arg-type]


def _mock_agent(output: object) -> AsyncMock:
    """Minimal agent mock — gathering nodes never call agents directly."""
    result = AsyncMock()
    result.output = output
    mock = AsyncMock()
    mock.run = AsyncMock(return_value=result)
    return mock


def _make_deps() -> ArcraDeps:
    return ArcraDeps(
        db_path=":memory:",
        resources_path=_RESOURCES_PATH,
        vagueness_agent=_mock_agent(AnomalyVaguenessResult(is_vague=False, missing_context="")),
        policy_extraction_agent=_mock_agent(PolicyRuleContainer(rules=[])),
    )


# ---------------------------------------------------------------------------
# 1. Pure helper — _find_invoice
# ---------------------------------------------------------------------------


class TestFindInvoice:
    def test_finds_known_invoice(self) -> None:
        """tx_100001 is present in acc_1001_1.md."""
        result = _find_invoice(_RESOURCES_PATH, "tx_100001")
        assert result is not None
        assert "acc_1001_1" in result

    def test_returns_none_for_unknown_tx(self) -> None:
        result = _find_invoice(_RESOURCES_PATH, "tx_NONEXISTENT_9999")
        assert result is None

    def test_finds_invoice_from_feed(self, xero_transactions: list[dict[str, object]]) -> None:
        """At least one real transaction in the feed has a matching invoice."""
        found = 0
        for tx in xero_transactions:
            if _find_invoice(_RESOURCES_PATH, str(tx["transaction_id"])) is not None:
                found += 1
        assert found >= 1, "Expected at least one invoice to match a feed transaction"


# ---------------------------------------------------------------------------
# 2. CheckDriveNode — evidence found path
# ---------------------------------------------------------------------------


class TestCheckDriveNodeFound:
    @pytest.mark.asyncio
    async def test_found_invoice_appends_evidence_and_ends(self) -> None:
        """tx_100001 has a matching invoice; graph should end with evidence_found."""
        state = _make_state(transaction=_make_tx(transaction_id="tx_100001"))
        deps = _make_deps()

        result = await gathering_graph.run(CheckDriveNode(), state=state, deps=deps)

        assert result.state.status == "evidence_found"
        assert len(result.state.evidence_documents) == 1
        assert "acc_1001_1" in result.state.evidence_documents[0]

    @pytest.mark.asyncio
    async def test_found_invoice_does_not_set_slack_ts(self) -> None:
        state = _make_state(transaction=_make_tx(transaction_id="tx_100001"))
        deps = _make_deps()
        result = await gathering_graph.run(CheckDriveNode(), state=state, deps=deps)
        assert result.state.slack_thread_ts is None


# ---------------------------------------------------------------------------
# 3. CheckDriveNode → DispatchSlackNode → SuspendForSlackNode (missing invoice)
# ---------------------------------------------------------------------------


class TestCheckDriveNodeMissing:
    @pytest.mark.asyncio
    async def test_missing_invoice_suspends_graph(self) -> None:
        """Unknown tx_id → full suspend path; state saved to DB."""
        tx_id = f"tx_UNKNOWN_{uuid.uuid4().hex[:8]}"
        state = _make_state(transaction=_make_tx(transaction_id=tx_id))
        deps = _make_deps()

        result = await gathering_graph.run(CheckDriveNode(), state=state, deps=deps)

        assert result.state.status == "awaiting_slack"
        assert result.state.slack_thread_ts is not None

    @pytest.mark.asyncio
    async def test_missing_invoice_saves_checkpoint(self) -> None:
        tx_id = f"tx_UNKNOWN_{uuid.uuid4().hex[:8]}"
        state = _make_state(transaction=_make_tx(transaction_id=tx_id))
        deps = _make_deps()

        result = await gathering_graph.run(CheckDriveNode(), state=state, deps=deps)

        record = await load_checkpoint(result.state.session_id)
        assert record is not None
        payload = record["checkpoint"]
        assert isinstance(payload, dict)
        assert payload["session_id"] == result.state.session_id

    @pytest.mark.asyncio
    async def test_missing_invoice_saves_interrupt(self) -> None:
        tx_id = f"tx_UNKNOWN_{uuid.uuid4().hex[:8]}"
        state = _make_state(transaction=_make_tx(transaction_id=tx_id))
        deps = _make_deps()

        result = await gathering_graph.run(CheckDriveNode(), state=state, deps=deps)

        interrupt = await load_interrupt(result.state.session_id)
        assert interrupt is not None
        assert interrupt["status"] == "awaiting_slack"
        assert interrupt["slack_message_ts"] == result.state.slack_thread_ts


# ---------------------------------------------------------------------------
# 4. load_state_from_checkpoint
# ---------------------------------------------------------------------------


class TestLoadStateFromCheckpoint:
    @pytest.mark.asyncio
    async def test_round_trip(self) -> None:
        state = _make_state(transaction=_make_tx(transaction_id="tx_100002"))
        payload = state.model_dump(mode="json")
        await save_checkpoint(
            thread_id=state.session_id,
            checkpoint_id=str(uuid.uuid4()),
            checkpoint_data=payload,
            metadata={"status": "awaiting_slack"},
        )
        loaded = await load_state_from_checkpoint(state.session_id)
        assert loaded is not None
        assert loaded.session_id == state.session_id
        assert loaded.transaction.transaction_id == "tx_100002"

    @pytest.mark.asyncio
    async def test_missing_session_returns_none(self) -> None:
        result = await load_state_from_checkpoint("nonexistent-session-id")
        assert result is None


# ---------------------------------------------------------------------------
# 5. load_interrupt_by_slack_ts
# ---------------------------------------------------------------------------


class TestLoadInterruptBySlackTs:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        session_id = str(uuid.uuid4())
        ts = "1234567890.123456"
        await save_interrupt(thread_id=session_id, status="awaiting_slack", slack_message_ts=ts)
        record = await load_interrupt_by_slack_ts(ts)
        assert record is not None
        assert record["thread_id"] == session_id

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        record = await load_interrupt_by_slack_ts("9999999999.000000")
        assert record is None


# ---------------------------------------------------------------------------
# 6. NormalizeToDriveNode (resumption path)
# ---------------------------------------------------------------------------


class TestNormalizeToDriveNode:
    @pytest.mark.asyncio
    async def test_slack_reply_appended_to_evidence(self) -> None:
        state = _make_state(
            transaction=_make_tx(transaction_id="tx_100003"),
            slack_thread_ts="1234567890.000001",
            slack_reply="https://drive.google.com/invoice_abc.pdf",
            status="awaiting_slack",
        )
        await save_interrupt(
            thread_id=state.session_id,
            status="awaiting_slack",
            slack_message_ts="1234567890.000001",
        )
        deps = _make_deps()
        result = await resumption_graph.run(NormalizeToDriveNode(), state=state, deps=deps)

        assert result.state.status == "evidence_gathered"
        assert len(result.state.evidence_documents) == 1
        assert "slack_reply://" in result.state.evidence_documents[0]

    @pytest.mark.asyncio
    async def test_empty_reply_still_sets_status(self) -> None:
        state = _make_state(
            transaction=_make_tx(transaction_id="tx_100004"),
            slack_thread_ts="1234567890.000002",
            slack_reply=None,
            status="awaiting_slack",
        )
        await save_interrupt(
            thread_id=state.session_id,
            status="awaiting_slack",
            slack_message_ts="1234567890.000002",
        )
        deps = _make_deps()
        result = await resumption_graph.run(NormalizeToDriveNode(), state=state, deps=deps)

        assert result.state.status == "evidence_gathered"
        assert len(result.state.evidence_documents) == 0

    @pytest.mark.asyncio
    async def test_interrupt_updated_to_resumed(self) -> None:
        session_id = str(uuid.uuid4())
        ts = "1234567890.000003"
        state = _make_state(
            transaction=_make_tx(transaction_id="tx_100005"),
            status="awaiting_slack",
            slack_thread_ts=ts,
            slack_reply="some evidence",
        )
        state = state.model_copy(update={"session_id": session_id})
        await save_interrupt(thread_id=session_id, status="awaiting_slack", slack_message_ts=ts)
        deps = _make_deps()
        await resumption_graph.run(NormalizeToDriveNode(), state=state, deps=deps)

        record = await load_interrupt(session_id)
        assert record is not None
        assert record["status"] == "resumed"


# ---------------------------------------------------------------------------
# 7. End-to-end: full Slack suspend → resume cycle
# ---------------------------------------------------------------------------


class TestFullSuspendResumeCycle:
    @pytest.mark.asyncio
    async def test_suspend_then_resume_produces_gathered_state(self) -> None:
        """Simulate a full cycle: unknown invoice → suspend → webhook → resume."""
        tx_id = f"tx_UNKNOWN_{uuid.uuid4().hex[:8]}"
        state = _make_state(transaction=_make_tx(transaction_id=tx_id))
        deps = _make_deps()

        # Phase 3a: run gathering graph — will suspend
        suspend_result = await gathering_graph.run(CheckDriveNode(), state=state, deps=deps)
        suspended_state = suspend_result.state
        assert suspended_state.status == "awaiting_slack"
        slack_ts = suspended_state.slack_thread_ts
        assert slack_ts is not None

        # Verify checkpoint + interrupt are persisted
        checkpoint = await load_checkpoint(suspended_state.session_id)
        assert checkpoint is not None
        interrupt_rec = await load_interrupt_by_slack_ts(slack_ts)
        assert interrupt_rec is not None

        # Phase 3b: simulate webhook — load state, inject reply, resume
        loaded_state = await load_state_from_checkpoint(suspended_state.session_id)
        assert loaded_state is not None
        loaded_state.slack_reply = "Invoice attached: inv_sjenkinis_12_03_2026.pdf"

        resume_result = await resumption_graph.run(
            NormalizeToDriveNode(), state=loaded_state, deps=deps
        )
        final_state = resume_result.state

        assert final_state.status == "evidence_gathered"
        assert len(final_state.evidence_documents) >= 1
        assert "slack_reply://" in final_state.evidence_documents[0]
