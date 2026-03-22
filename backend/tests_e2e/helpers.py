"""Shared pure helper functions for e2e prompt evaluation tests.

These are stateless utilities intentionally kept separate from conftest.py
so they can be imported by both conftest and individual test modules without
triggering any pytest fixture machinery.
"""
from __future__ import annotations

import json
import os
from typing import Any

from src.graph.state import XeroTransaction

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_ROOT, ".."))

XERO_FEED_PATH: str = os.path.join(_REPO_ROOT, "resources", "xero_api_feed.json")
POLICIES_DIR: str = os.path.join(_REPO_ROOT, "resources", "policies")


def load_all_transactions() -> list[dict[str, Any]]:
    """Flatten the multi-account xero_api_feed.json into a single transaction list.

    Per AGENTS.md §4 — no dummy dicts; real fixture data only.
    """
    with open(XERO_FEED_PATH) as fh:
        data: list[dict[str, Any]] = json.load(fh)
    txs: list[dict[str, Any]] = []
    for account in data:
        txs.extend(account["transactions"])
    return txs


def find_transaction(txs: list[dict[str, Any]], tx_id: str) -> XeroTransaction:
    """Return a typed XeroTransaction for the given ID or raise KeyError."""
    for tx in txs:
        if tx["transaction_id"] == tx_id:
            return XeroTransaction(
                transaction_id=tx["transaction_id"],
                date=tx["date"],
                description=tx["description"],
                amount=float(tx["amount"]),
                currency=tx["currency"],
                type=tx["type"],
            )
    raise KeyError(f"Transaction {tx_id!r} not found in xero_api_feed.json")


def load_policy_content(filename: str) -> str:
    """Read and return the full text of a policy markdown file.

    Per PLAN_OVERRIDE §5 — only the deterministically routed policy file is
    loaded; the caller is responsible for selecting the right file.
    """
    path = os.path.join(POLICIES_DIR, filename)
    with open(path) as fh:
        return fh.read()


def build_transaction_prompt(tx: XeroTransaction) -> str:
    """Render a canonical vagueness-analysis prompt string for a transaction."""
    return (
        f"Analyse this transaction for vagueness and extract any identifying entities:\n"
        f"Transaction ID: {tx.transaction_id}\n"
        f"Date: {tx.date}\n"
        f"Description: {tx.description}\n"
        f"Amount: {tx.amount} {tx.currency}\n"
        f"Type: {tx.type}"
    )
