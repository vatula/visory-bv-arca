from __future__ import annotations

import json
import os
from typing import TypedDict

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.db import get_connection

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["queue"])


class _RawTransaction(TypedDict):
    transaction_id: str
    date: str
    description: str
    amount: float
    currency: str
    type: str


class _RawBankAccount(TypedDict):
    bank_account_id: str
    transactions: list[_RawTransaction]


class QueuedTransaction(BaseModel):
    transaction_id: str
    date: str
    description: str
    amount: float
    currency: str
    type: str
    bank_account_id: str | None = None


class QueueResponse(BaseModel):
    queue: list[QueuedTransaction]
    total_remaining: int


@router.get(
    "/queue",
    response_model=QueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the next 10 unprocessed transactions from xero_api_feed.json",
)
async def get_queue() -> QueueResponse:
    """Read xero_api_feed.json from resources_path, filter out already-known transaction
    IDs, and return at most the next 10 unprocessed transactions in feed order."""
    settings = get_settings()
    feed_path = os.path.join(settings.resources_path, "xero_api_feed.json")

    try:
        with open(feed_path) as fh:
            feed: list[object] = json.load(fh)
    except FileNotFoundError as exc:
        logger.error("xero_feed_not_found", feed_path=feed_path, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feed file not found: {feed_path}",
        ) from exc

    feed_typed: list[_RawBankAccount] = json.loads(
        json.dumps(feed)
    )
    all_txs: list[QueuedTransaction] = []
    for bank_account in feed_typed:
        bank_account_id = bank_account.get("bank_account_id", "unknown")
        for raw_tx in bank_account.get("transactions", []):
            all_txs.append(
                QueuedTransaction(
                    transaction_id=raw_tx["transaction_id"],
                    date=raw_tx["date"],
                    description=raw_tx["description"],
                    amount=raw_tx["amount"],
                    currency=raw_tx["currency"],
                    type=raw_tx["type"],
                    bank_account_id=bank_account_id,
                )
            )

    async with get_connection() as conn:
        cursor = await conn.execute("SELECT transaction_id FROM arcra_ui_read_model")
        known_ids = {row["transaction_id"] for row in await cursor.fetchall()}

    remaining = [tx for tx in all_txs if tx.transaction_id not in known_ids]

    logger.info("queue_queried", total_remaining=len(remaining))
    return QueueResponse(queue=remaining[:10], total_remaining=len(remaining))
