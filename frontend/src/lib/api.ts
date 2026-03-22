import { z } from "zod";
import {
  ActiveTransactionsResponseSchema,
  ProcessedTransactionsResponseSchema,
  QueueResponseSchema,
  TransactionAuditResponseSchema,
  type ActiveTransactionsResponse,
  type ProcessedTransactionsResponse,
  type QueuedTransaction,
  type QueueResponse,
  type TransactionAuditResponse,
} from "@/types/schemas";
import { getComponentLogger } from "@/lib/logger";

const log = getComponentLogger("api");

// Client-side: relative URL resolves to the browser's current origin, hitting the
// Next.js catch-all proxy at /app/api/[...path]/route.ts.
// Server-side (RSC/SSR): relative URLs have no host context, so we must use the
// Docker-internal backend URL directly via INTERNAL_API_URL.
const BFF_BASE =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_URL ?? "http://localhost:8000")
    : "";

// The SSE stream is consumed directly by the browser via EventSource. It must
// bypass the Next.js proxy and connect to the backend port exposed on the host.
const SSE_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Internal helper — fetch + Zod parse with structured error logging
// ---------------------------------------------------------------------------

async function fetchAndParse<T>(
  url: string,
  schema: z.ZodType<T>,
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store" });
  } catch (err) {
    log.error({ err, url }, "network_fetch_failed");
    throw new Error(`Network error fetching ${url}`);
  }

  if (!res.ok) {
    log.error({ url, status: res.status, statusText: res.statusText }, "api_response_error");
    throw new Error(`API error ${res.status} from ${url}`);
  }

  let raw: unknown;
  try {
    raw = await res.json();
  } catch (err) {
    log.error({ err, url }, "api_json_parse_failed");
    throw new Error(`Failed to parse JSON from ${url}`);
  }

  const parsed = schema.safeParse(raw);
  if (!parsed.success) {
    log.error({ url, issues: parsed.error.issues }, "api_schema_validation_failed");
    throw new Error(`Schema validation failed for ${url}`);
  }

  log.debug({ url }, "api_fetch_success");
  return parsed.data;
}

// ---------------------------------------------------------------------------
// Public API helpers
// ---------------------------------------------------------------------------

export async function fetchActiveTransactions(): Promise<ActiveTransactionsResponse> {
  return fetchAndParse(
    `${BFF_BASE}/api/v1/transactions/active`,
    ActiveTransactionsResponseSchema,
  );
}

export async function fetchProcessedTransactions(): Promise<ProcessedTransactionsResponse> {
  return fetchAndParse(
    `${BFF_BASE}/api/v1/transactions/processed`,
    ProcessedTransactionsResponseSchema,
  );
}

export async function fetchTransactionAudit(
  id: string,
): Promise<TransactionAuditResponse> {
  return fetchAndParse(
    `${BFF_BASE}/api/v1/transactions/${encodeURIComponent(id)}/audit`,
    TransactionAuditResponseSchema,
  );
}

export async function fetchQueue(): Promise<QueueResponse> {
  return fetchAndParse(`${BFF_BASE}/api/v1/queue`, QueueResponseSchema);
}

const ProcessResponseSchema = z.object({
  transaction_id: z.string(),
  status: z.string(),
});

export async function submitTransaction(tx: QueuedTransaction): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BFF_BASE}/api/v1/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tx),
      cache: "no-store",
    });
  } catch (err) {
    log.error({ err, transaction_id: tx.transaction_id }, "submit_transaction_network_failed");
    throw new Error(`Network error submitting ${tx.transaction_id}`);
  }

  if (!res.ok) {
    log.error({ status: res.status, transaction_id: tx.transaction_id }, "submit_transaction_failed");
    throw new Error(`Process API error ${res.status} for ${tx.transaction_id}`);
  }

  let raw: unknown;
  try {
    raw = await res.json();
  } catch (err) {
    log.warn({ err, transaction_id: tx.transaction_id }, "submit_transaction_response_parse_failed");
    return;
  }

  const parsed = ProcessResponseSchema.safeParse(raw);
  if (!parsed.success) {
    log.warn({ issues: parsed.error.issues, transaction_id: tx.transaction_id }, "submit_transaction_response_invalid");
    return;
  }

  log.info({ transaction_id: parsed.data.transaction_id, status: parsed.data.status }, "transaction_submitted");
}

const ResetResponseSchema = z.object({
  message: z.string(),
  rows_deleted_ui_read_model: z.number(),
  rows_deleted_audit_events: z.number(),
});

export type ResetResponse = z.infer<typeof ResetResponseSchema>;

export async function resetState(): Promise<ResetResponse> {
  let res: Response;
  try {
    res = await fetch(`${BFF_BASE}/api/v1/reset`, {
      method: "POST",
      cache: "no-store",
    });
  } catch (err) {
    log.error({ err }, "reset_state_network_failed");
    throw new Error("Network error calling reset");
  }

  if (!res.ok) {
    log.error({ status: res.status }, "reset_state_failed");
    throw new Error(`Reset API error ${res.status}`);
  }

  let raw: unknown;
  try {
    raw = await res.json();
  } catch (err) {
    log.error({ err }, "reset_state_response_parse_failed");
    throw new Error("Failed to parse reset response");
  }

  const parsed = ResetResponseSchema.safeParse(raw);
  if (!parsed.success) {
    log.error({ issues: parsed.error.issues }, "reset_state_response_invalid");
    throw new Error("Schema validation failed for reset response");
  }

  log.info(
    {
      rows_deleted_ui_read_model: parsed.data.rows_deleted_ui_read_model,
      rows_deleted_audit_events: parsed.data.rows_deleted_audit_events,
    },
    "state_reset",
  );
  return parsed.data;
}

// ---------------------------------------------------------------------------
// SSE stream URL (consumed directly via native EventSource in components)
// ---------------------------------------------------------------------------

export function getSseStreamUrl(): string {
  return `${SSE_BASE}/api/v1/stream`;
}
