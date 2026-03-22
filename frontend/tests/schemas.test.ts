import { describe, it, expect } from "vitest";
import {
  TransactionSummarySchema,
  AuditEventSchema,
  TransactionAuditResponseSchema,
  ActiveTransactionsResponseSchema,
  ProcessedTransactionsResponseSchema,
  TransactionStatusSchema,
  getStatusMeta,
} from "@/types/schemas";

const validSummary = {
  transaction_id: "tx_001",
  status: "complete",
  amount: -450.0,
  merchant: "AWS",
  employee_name: "Alice",
  confidence_score: 0.92,
  synthesis_reasoning: "Matched cloud policy.",
  last_updated: "2026-01-01T00:00:00",
};

const validAuditEvent = {
  id: 1,
  transaction_id: "tx_001",
  timestamp: "2026-01-01T00:00:00",
  node_name: "PolicyGraph",
  action_summary: "Extracted cloud rule.",
  slack_channel: null,
  slack_message_sent: null,
  slack_reply_received: null,
};

describe("TransactionStatusSchema", () => {
  it("accepts all valid status values", () => {
    const statuses = [
      "pending",
      "processing",
      "policy_check",
      "evidence_gathering",
      "awaiting_slack",
      "complete",
      "escalated",
    ];
    for (const s of statuses) {
      expect(TransactionStatusSchema.parse(s)).toBe(s);
    }
  });

  it("rejects unknown status", () => {
    expect(() => TransactionStatusSchema.parse("unknown_status")).toThrow();
  });
});

describe("TransactionSummarySchema", () => {
  it("parses a valid summary", () => {
    const result = TransactionSummarySchema.parse(validSummary);
    expect(result.transaction_id).toBe("tx_001");
    expect(result.confidence_score).toBe(0.92);
  });

  it("accepts null nullable fields", () => {
    const result = TransactionSummarySchema.parse({
      ...validSummary,
      amount: null,
      merchant: null,
      employee_name: null,
      confidence_score: null,
      synthesis_reasoning: null,
    });
    expect(result.amount).toBeNull();
    expect(result.merchant).toBeNull();
  });

  it("rejects missing required fields", () => {
    expect(() =>
      TransactionSummarySchema.parse({ transaction_id: "tx_001" }),
    ).toThrow();
  });

  it("rejects confidence_score outside [0,1]", () => {
    expect(() =>
      TransactionSummarySchema.parse({ ...validSummary, confidence_score: 1.5 }),
    ).toThrow();
    expect(() =>
      TransactionSummarySchema.parse({ ...validSummary, confidence_score: -0.1 }),
    ).toThrow();
  });
});

describe("AuditEventSchema", () => {
  it("parses a valid audit event", () => {
    const result = AuditEventSchema.parse(validAuditEvent);
    expect(result.id).toBe(1);
    expect(result.node_name).toBe("PolicyGraph");
  });

  it("accepts slack fields populated", () => {
    const result = AuditEventSchema.parse({
      ...validAuditEvent,
      slack_channel: "finance",
      slack_message_sent: "Please provide receipt.",
      slack_reply_received: "Here it is.",
    });
    expect(result.slack_channel).toBe("finance");
    expect(result.slack_reply_received).toBe("Here it is.");
  });
});

describe("TransactionAuditResponseSchema", () => {
  it("parses transaction + audit trail", () => {
    const result = TransactionAuditResponseSchema.parse({
      transaction: validSummary,
      audit_trail: [validAuditEvent],
    });
    expect(result.audit_trail).toHaveLength(1);
  });

  it("accepts empty audit trail", () => {
    const result = TransactionAuditResponseSchema.parse({
      transaction: validSummary,
      audit_trail: [],
    });
    expect(result.audit_trail).toHaveLength(0);
  });
});

describe("ActiveTransactionsResponseSchema", () => {
  it("parses active list", () => {
    const result = ActiveTransactionsResponseSchema.parse({
      active: [validSummary],
    });
    expect(result.active).toHaveLength(1);
  });
});

describe("ProcessedTransactionsResponseSchema", () => {
  it("parses processed list", () => {
    const result = ProcessedTransactionsResponseSchema.parse({
      processed: [validSummary],
    });
    expect(result.processed).toHaveLength(1);
  });
});

describe("getStatusMeta", () => {
  it("returns correct label for every status", () => {
    expect(getStatusMeta("pending").label).toBe("Pending");
    expect(getStatusMeta("processing").label).toBe("Processing");
    expect(getStatusMeta("policy_check").label).toBe("Policy Check");
    expect(getStatusMeta("evidence_gathering").label).toBe("Gathering Evidence");
    expect(getStatusMeta("awaiting_slack").label).toBe("Awaiting Slack");
    expect(getStatusMeta("complete").label).toBe("Complete");
    expect(getStatusMeta("escalated").label).toBe("Escalated");
  });

  it("returns distinct colours per status", () => {
    const colours = new Set(
      (
        [
          "pending",
          "processing",
          "policy_check",
          "evidence_gathering",
          "awaiting_slack",
          "complete",
          "escalated",
        ] as const
      ).map((s) => getStatusMeta(s).colour),
    );
    expect(colours.size).toBe(7);
  });
});
