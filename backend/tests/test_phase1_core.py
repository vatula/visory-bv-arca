"""Phase 1 tests: DB initialisation, WAL mode, schema integrity, and telemetry multiplexer."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest
import structlog

from src.core.config import Settings, get_settings  # type: ignore[import]
from src.core.db import (  # type: ignore[import]
    get_connection,
    init_db,
    insert_audit_event,
    load_checkpoint,
    load_interrupt,
    save_checkpoint,
    save_interrupt,
    upsert_ui_read_model,
)
from src.core.logging import TelemetryProcessor  # type: ignore[import]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db(tmp_path: object) -> str:
    """Return a path to a temporary SQLite database file."""
    return str(tmp_path) + "/test_arcra.db"  # type: ignore[operator]


@pytest.fixture()
def patched_settings(tmp_db: str) -> Settings:
    """Override DATABASE_URL to point at the temporary test database."""
    settings = Settings(database_url=tmp_db)
    with patch("src.core.db.get_settings", return_value=settings), \
         patch("src.core.config._settings", settings):
        yield settings  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DB initialisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_db_creates_all_tables(patched_settings: Settings) -> None:
    """init_db() must create all four required tables."""
    await init_db()

    async with aiosqlite.connect(patched_settings.database_url) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in await cursor.fetchall()}

    assert "arcra_checkpoints" in tables
    assert "arcra_interrupts" in tables
    assert "arcra_audit_events" in tables
    assert "arcra_ui_read_model" in tables


@pytest.mark.asyncio
async def test_init_db_enables_wal_mode(patched_settings: Settings) -> None:
    """init_db() must set journal_mode to WAL."""
    await init_db()

    async with aiosqlite.connect(patched_settings.database_url) as conn:
        cursor = await conn.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "wal"


@pytest.mark.asyncio
async def test_get_connection_enforces_wal(patched_settings: Settings) -> None:
    """get_connection() must enforce WAL on every new connection."""
    await init_db()

    async with get_connection() as conn:
        cursor = await conn.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "wal"


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_audit_event(patched_settings: Settings) -> None:
    """insert_audit_event() must persist a row in arcra_audit_events."""
    await init_db()

    await insert_audit_event(
        transaction_id="tx_test_001",
        node_name="TestNode",
        action_summary="Unit test event",
    )

    async with aiosqlite.connect(patched_settings.database_url) as conn:
        cursor = await conn.execute(
            "SELECT * FROM arcra_audit_events WHERE transaction_id = ?", ("tx_test_001",)
        )
        row = await cursor.fetchone()

    assert row is not None
    assert row[3] == "TestNode"
    assert row[4] == "Unit test event"


@pytest.mark.asyncio
async def test_upsert_ui_read_model_insert_and_update(patched_settings: Settings) -> None:
    """upsert_ui_read_model() must insert on first call and update on second."""
    await init_db()

    await upsert_ui_read_model("tx_test_002", status="pending", amount=250.0, merchant="Acme")
    await upsert_ui_read_model("tx_test_002", status="processing", confidence_score=0.88)

    async with aiosqlite.connect(patched_settings.database_url) as conn:
        cursor = await conn.execute(
            "SELECT status, amount, merchant, confidence_score FROM arcra_ui_read_model WHERE transaction_id = ?",
            ("tx_test_002",),
        )
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "processing"
    assert row[1] == 250.0        # preserved from first upsert
    assert row[2] == "Acme"       # preserved from first upsert
    assert row[3] == 0.88         # set on second upsert


@pytest.mark.asyncio
async def test_save_and_load_checkpoint(patched_settings: Settings) -> None:
    """save_checkpoint() / load_checkpoint() must round-trip the graph state."""
    await init_db()

    state_payload = {"session_id": "tx_003", "anomaly": True}
    meta_payload = {"status": "processing"}

    await save_checkpoint(
        thread_id="tx_003",
        checkpoint_id="ckpt_001",
        checkpoint_data=state_payload,
        metadata=meta_payload,
    )

    result = await load_checkpoint("tx_003")

    assert result is not None
    assert result["checkpoint"] == state_payload
    assert result["metadata"] == meta_payload
    assert result["checkpoint_id"] == "ckpt_001"


@pytest.mark.asyncio
async def test_save_and_load_interrupt(patched_settings: Settings) -> None:
    """save_interrupt() / load_interrupt() must round-trip the interrupt record."""
    await init_db()

    await save_interrupt(
        thread_id="tx_004",
        status="awaiting_slack",
        slack_message_ts="1234567890.000100",
    )

    result = await load_interrupt("tx_004")

    assert result is not None
    assert result["status"] == "awaiting_slack"
    assert result["slack_message_ts"] == "1234567890.000100"


@pytest.mark.asyncio
async def test_load_checkpoint_returns_none_for_missing(patched_settings: Settings) -> None:
    """load_checkpoint() must return None for an unknown thread_id."""
    await init_db()
    result = await load_checkpoint("nonexistent_thread")
    assert result is None


# ---------------------------------------------------------------------------
# TelemetryProcessor
# ---------------------------------------------------------------------------


def test_telemetry_processor_strips_flag_from_event_dict() -> None:
    """TelemetryProcessor must remove is_telemetry from the event dict."""
    processor = TelemetryProcessor()
    event_dict = {
        "event": "policy_extracted",
        "is_telemetry": True,
        "transaction_id": "tx_005",
        "node": "PolicyNode",
        "action_summary": "Policy matched",
    }

    with patch("src.core.logging.asyncio.get_running_loop") as mock_loop:
        mock_task_loop = MagicMock()
        mock_task_loop.create_task.side_effect = lambda coro, **kw: coro.close()
        mock_loop.return_value = mock_task_loop

        result = processor(MagicMock(), "info", event_dict)

    assert "is_telemetry" not in result


def test_telemetry_processor_dispatches_create_task_when_flagged() -> None:
    """TelemetryProcessor must call loop.create_task() for telemetry events."""
    processor = TelemetryProcessor()
    event_dict = {
        "event": "anomaly_detected",
        "is_telemetry": True,
        "transaction_id": "tx_006",
        "node": "AnomalyNode",
        "action_summary": "High-value transaction detected",
    }

    with patch("src.core.logging.asyncio.get_running_loop") as mock_loop:
        mock_task_loop = MagicMock()
        mock_task_loop.create_task.side_effect = lambda coro, **kw: coro.close()
        mock_loop.return_value = mock_task_loop

        processor(MagicMock(), "info", event_dict)

    mock_task_loop.create_task.assert_called_once()


def test_telemetry_processor_passes_through_non_telemetry_events() -> None:
    """TelemetryProcessor must not dispatch any task for regular log events."""
    processor = TelemetryProcessor()
    event_dict = {"event": "regular_log", "detail": "nothing special"}

    with patch("src.core.logging.asyncio.get_running_loop") as mock_loop:
        mock_task_loop = MagicMock()
        mock_task_loop.create_task.side_effect = lambda coro, **kw: coro.close()
        mock_loop.return_value = mock_task_loop

        result = processor(MagicMock(), "info", event_dict)

    mock_task_loop.create_task.assert_not_called()
    assert result["event"] == "regular_log"


def test_telemetry_processor_handles_missing_event_loop_gracefully() -> None:
    """TelemetryProcessor must not raise when no event loop is running."""
    processor = TelemetryProcessor()
    event_dict = {
        "event": "node_run",
        "is_telemetry": True,
        "transaction_id": "tx_007",
        "node": "SomeNode",
        "action_summary": "Ran",
    }

    with patch("src.core.logging.asyncio.get_running_loop", side_effect=RuntimeError("no loop")):
        # Must not raise
        result = processor(MagicMock(), "info", event_dict)

    assert "is_telemetry" not in result
