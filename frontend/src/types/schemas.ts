import { z } from "zod";

// ---------------------------------------------------------------------------
// Transaction status — discriminated union
// ---------------------------------------------------------------------------

export const TransactionStatusSchema = z.enum([
  "pending",
  "processing",
  "suspended",
  "policy_check",
  "evidence_gathering",
  "awaiting_slack",
  "evidence_found",
  "complete",
  "resolved",
  "escalated",
]);

export type TransactionStatus = z.infer<typeof TransactionStatusSchema>;

// ---------------------------------------------------------------------------
// Core domain schemas (mirroring FastAPI response models)
// ---------------------------------------------------------------------------

export const TransactionSummarySchema = z.object({
  transaction_id: z.string(),
  status: TransactionStatusSchema,
  amount: z.number().nullable(),
  merchant: z.string().nullable(),
  employee_name: z.string().nullable(),
  confidence_score: z.number().min(0).max(1).nullable(),
  synthesis_reasoning: z.string().nullable(),
  last_updated: z.string(),
});

export type TransactionSummary = z.infer<typeof TransactionSummarySchema>;

export const AuditEventSchema = z.object({
  id: z.number(),
  transaction_id: z.string(),
  timestamp: z.string(),
  node_name: z.string(),
  action_summary: z.string(),
  slack_channel: z.string().nullable(),
  slack_message_sent: z.string().nullable(),
  slack_reply_received: z.string().nullable(),
});

export type AuditEvent = z.infer<typeof AuditEventSchema>;

export const TransactionAuditResponseSchema = z.object({
  transaction: TransactionSummarySchema,
  audit_trail: z.array(AuditEventSchema),
});

export type TransactionAuditResponse = z.infer<
  typeof TransactionAuditResponseSchema
>;

export const ActiveTransactionsResponseSchema = z.object({
  active: z.array(TransactionSummarySchema),
});

export type ActiveTransactionsResponse = z.infer<
  typeof ActiveTransactionsResponseSchema
>;

export const ProcessedTransactionsResponseSchema = z.object({
  processed: z.array(TransactionSummarySchema),
});

export type ProcessedTransactionsResponse = z.infer<
  typeof ProcessedTransactionsResponseSchema
>;

// ---------------------------------------------------------------------------
// SSE event payload
// ---------------------------------------------------------------------------

export const SseEventSchema = z.object({
  type: z.enum(["active_update", "processed_update", "heartbeat"]),
  data: z.unknown(),
});

export type SseEvent = z.infer<typeof SseEventSchema>;

// ---------------------------------------------------------------------------
// UI state — discriminated union for dashboard feed
// ---------------------------------------------------------------------------

export type DashboardState =
  | { readonly kind: "loading" }
  | { readonly kind: "error"; readonly message: string }
  | {
      readonly kind: "ready";
      readonly active: readonly TransactionSummary[];
      readonly processed: readonly TransactionSummary[];
    };

// ---------------------------------------------------------------------------
// Status display metadata
// ---------------------------------------------------------------------------

export interface StatusMeta {
  readonly label: string;
  readonly colour: string;
  readonly bgColour: string;
}

export function getStatusMeta(status: TransactionStatus): StatusMeta {
  switch (status) {
    case "pending":
      return { label: "Pending", colour: "text-indigo-300", bgColour: "bg-indigo-900/40" };
    case "processing":
      return { label: "Processing", colour: "text-amber-300", bgColour: "bg-amber-900/40" };
    case "policy_check":
      return { label: "Policy Check", colour: "text-violet-300", bgColour: "bg-violet-900/40" };
    case "evidence_gathering":
      return { label: "Gathering Evidence", colour: "text-blue-300", bgColour: "bg-blue-900/40" };
    case "awaiting_slack":
      return { label: "Awaiting Slack", colour: "text-orange-300", bgColour: "bg-orange-900/40" };
    case "complete":
      return { label: "Complete", colour: "text-green-300", bgColour: "bg-green-900/40" };
    case "suspended":
      return { label: "Suspended", colour: "text-yellow-300", bgColour: "bg-yellow-900/40" };
    case "evidence_found":
      return { label: "Evidence Found", colour: "text-teal-300", bgColour: "bg-teal-900/40" };
    case "resolved":
      return { label: "Resolved", colour: "text-green-300", bgColour: "bg-green-900/40" };
    case "escalated":
      return { label: "Escalated", colour: "text-red-300", bgColour: "bg-red-900/40" };
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}
