import { describe, it, expect, vi, afterEach } from "vitest";
import { type QueuedTransaction } from "@/types/schemas";

vi.mock("@/lib/logger", () => ({
  getComponentLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

// Import after mock so the module resolves with the mocked logger
const { fetchQueue, submitTransaction, fetchActiveTransactions, fetchProcessedTransactions, fetchTransactionAudit, resetState } =
  await import("@/lib/api");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeOkResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => body,
  } as unknown as Response;
}

function makeErrorResponse(status: number): Response {
  return {
    ok: false,
    status,
    statusText: "Error",
    json: async () => ({}),
  } as unknown as Response;
}

const mockQueueResponse = {
  queue: [
    {
      transaction_id: "tx_001",
      date: "2026-01-15",
      description: "AWS Cloud Services",
      amount: -450.0,
      currency: "AUD",
      type: "DEBIT",
      bank_account_id: "acc_001",
    },
  ],
  total_remaining: 52,
};

const mockQueuedTx: QueuedTransaction = {
  transaction_id: "tx_001",
  date: "2026-01-15",
  description: "AWS Cloud Services",
  amount: -450.0,
  currency: "AUD",
  type: "DEBIT",
  bank_account_id: "acc_001",
};

const mockAuditResponse = {
  transaction: {
    transaction_id: "tx_100045",
    status: "escalated",
    amount: 120.0,
    merchant: "CAFE SYDNEY",
    employee_name: null,
    confidence_score: 0.5,
    synthesis_reasoning: "Insufficient evidence.",
    last_updated: "2026-03-22T12:52:29.053417+00:00",
  },
  audit_trail: [
    {
      id: 1,
      transaction_id: "tx_100045",
      timestamp: "2026-03-22T12:52:26.198130+00:00",
      node_name: "EvaluateVaguenessNode",
      action_summary: "Calling Bedrock for entity extraction: CAFE SYDNEY",
      slack_channel: null,
      slack_message_sent: null,
      slack_reply_received: null,
    },
  ],
};

// ---------------------------------------------------------------------------
// fetchQueue
// ---------------------------------------------------------------------------

describe("fetchQueue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed QueueResponse on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeOkResponse(mockQueueResponse)));
    const result = await fetchQueue();
    expect(result.total_remaining).toBe(52);
    expect(result.queue).toHaveLength(1);
    expect(result.queue[0]?.transaction_id).toBe("tx_001");
  });

  it("calls the correct endpoint", async () => {
    const mockFetch = vi.fn().mockResolvedValue(makeOkResponse(mockQueueResponse));
    vi.stubGlobal("fetch", mockFetch);
    await fetchQueue();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/queue"),
      expect.any(Object),
    );
  });

  it("throws on non-ok HTTP response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeErrorResponse(500)));
    await expect(fetchQueue()).rejects.toThrow("API error 500");
  });

  it("throws when response shape does not match schema", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeOkResponse({ unexpected: "shape" })));
    await expect(fetchQueue()).rejects.toThrow("Schema validation failed");
  });

  it("throws on network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network down")));
    await expect(fetchQueue()).rejects.toThrow("Network error");
  });

  it("accepts an empty queue array", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(makeOkResponse({ queue: [], total_remaining: 0 })),
    );
    const result = await fetchQueue();
    expect(result.queue).toHaveLength(0);
    expect(result.total_remaining).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// submitTransaction
// ---------------------------------------------------------------------------

describe("submitTransaction", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("resolves without error on successful submit", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        makeOkResponse({ transaction_id: "tx_001", status: "pending" }),
      ),
    );
    await expect(submitTransaction(mockQueuedTx)).resolves.toBeUndefined();
  });

  it("POSTs to /api/v1/process with correct method and JSON body", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      makeOkResponse({ transaction_id: "tx_001", status: "pending" }),
    );
    vi.stubGlobal("fetch", mockFetch);
    await submitTransaction(mockQueuedTx);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/process"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("tx_001"),
      }),
    );
  });

  it("sends Content-Type: application/json header", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      makeOkResponse({ transaction_id: "tx_001", status: "pending" }),
    );
    vi.stubGlobal("fetch", mockFetch);
    await submitTransaction(mockQueuedTx);
    const callArgs = mockFetch.mock.calls[0] as [string, RequestInit];
    const headers = callArgs[1].headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("throws on non-ok HTTP response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeErrorResponse(422)));
    await expect(submitTransaction(mockQueuedTx)).rejects.toThrow("Process API error 422");
  });

  it("throws on network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network down")));
    await expect(submitTransaction(mockQueuedTx)).rejects.toThrow("Network error");
  });

  it("resolves gracefully when response body is not valid JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => { throw new Error("invalid json"); },
    } as unknown as Response));
    await expect(submitTransaction(mockQueuedTx)).resolves.toBeUndefined();
  });

  it("resolves gracefully when response schema does not match (warn path)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(makeOkResponse({ unexpected: "fields" })),
    );
    await expect(submitTransaction(mockQueuedTx)).resolves.toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// fetchTransactionAudit
// ---------------------------------------------------------------------------

describe("fetchTransactionAudit", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed TransactionAuditResponse on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeOkResponse(mockAuditResponse)));
    const result = await fetchTransactionAudit("tx_100045");
    expect(result.transaction.transaction_id).toBe("tx_100045");
    expect(result.transaction.status).toBe("escalated");
    expect(result.audit_trail).toHaveLength(1);
    expect(result.audit_trail[0]?.node_name).toBe("EvaluateVaguenessNode");
  });

  it("calls the correct endpoint with encoded transaction id", async () => {
    const mockFetch = vi.fn().mockResolvedValue(makeOkResponse(mockAuditResponse));
    vi.stubGlobal("fetch", mockFetch);
    await fetchTransactionAudit("tx_100045");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/transactions/tx_100045/audit"),
      expect.any(Object),
    );
  });

  it("encodes special characters in transaction id", async () => {
    const mockFetch = vi.fn().mockResolvedValue(makeOkResponse(mockAuditResponse));
    vi.stubGlobal("fetch", mockFetch);
    await fetchTransactionAudit("tx/special id");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("tx%2Fspecial%20id"),
      expect.any(Object),
    );
  });

  it("throws on 404 response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeErrorResponse(404)));
    await expect(fetchTransactionAudit("tx_unknown")).rejects.toThrow("API error 404");
  });

  it("throws on network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network down")));
    await expect(fetchTransactionAudit("tx_100045")).rejects.toThrow("Network error");
  });

  it("throws when response shape does not match schema", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeOkResponse({ unexpected: true })));
    await expect(fetchTransactionAudit("tx_100045")).rejects.toThrow("Schema validation failed");
  });

  it("accepts an empty audit_trail array", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        makeOkResponse({ ...mockAuditResponse, audit_trail: [] }),
      ),
    );
    const result = await fetchTransactionAudit("tx_100045");
    expect(result.audit_trail).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// fetchActiveTransactions
// ---------------------------------------------------------------------------

describe("fetchActiveTransactions", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed active transactions on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(makeOkResponse({ active: [] })),
    );
    const result = await fetchActiveTransactions();
    expect(result.active).toHaveLength(0);
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeErrorResponse(503)));
    await expect(fetchActiveTransactions()).rejects.toThrow("API error 503");
  });

  it.each([
    "pending",
    "processing",
    "suspended",
    "policy_check",
    "evidence_gathering",
    "awaiting_slack",
    "evidence_found",
  ] as const)(
    "accepts active transaction with intermediate status %s",
    async (status) => {
      const tx = {
        transaction_id: "tx_active_001",
        status,
        amount: 100.0,
        merchant: "ACME",
        employee_name: null,
        confidence_score: null,
        synthesis_reasoning: null,
        last_updated: "2026-03-22T12:00:00.000000+00:00",
      };
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(makeOkResponse({ active: [tx] })),
      );
      const result = await fetchActiveTransactions();
      expect(result.active[0]?.status).toBe(status);
    },
  );
});

// ---------------------------------------------------------------------------
// fetchProcessedTransactions
// ---------------------------------------------------------------------------

describe("fetchProcessedTransactions", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed processed transactions on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(makeOkResponse({ processed: [] })),
    );
    const result = await fetchProcessedTransactions();
    expect(result.processed).toHaveLength(0);
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeErrorResponse(404)));
    await expect(fetchProcessedTransactions()).rejects.toThrow("API error 404");
  });
});

// ---------------------------------------------------------------------------
// resetState
// ---------------------------------------------------------------------------

const mockResetResponse = {
  message: "Application state reset successfully.",
  rows_deleted_ui_read_model: 52,
  rows_deleted_audit_events: 104,
};

describe("resetState", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed ResetResponse on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeOkResponse(mockResetResponse)));
    const result = await resetState();
    expect(result.message).toBe("Application state reset successfully.");
    expect(result.rows_deleted_ui_read_model).toBe(52);
    expect(result.rows_deleted_audit_events).toBe(104);
  });

  it("POSTs to /api/v1/reset", async () => {
    const mockFetch = vi.fn().mockResolvedValue(makeOkResponse(mockResetResponse));
    vi.stubGlobal("fetch", mockFetch);
    await resetState();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/reset"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok HTTP response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeErrorResponse(500)));
    await expect(resetState()).rejects.toThrow("Reset API error 500");
  });

  it("throws on network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network down")));
    await expect(resetState()).rejects.toThrow("Network error calling reset");
  });

  it("throws when response body is not valid JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => { throw new Error("invalid json"); },
    } as unknown as Response));
    await expect(resetState()).rejects.toThrow("Failed to parse reset response");
  });

  it("throws when response schema does not match", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeOkResponse({ unexpected: true })));
    await expect(resetState()).rejects.toThrow("Schema validation failed");
  });

  it("accepts zero row counts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        makeOkResponse({ ...mockResetResponse, rows_deleted_ui_read_model: 0, rows_deleted_audit_events: 0 }),
      ),
    );
    const result = await resetState();
    expect(result.rows_deleted_ui_read_model).toBe(0);
    expect(result.rows_deleted_audit_events).toBe(0);
  });
});
