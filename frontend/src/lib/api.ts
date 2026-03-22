import { z } from "zod";
import {
  ActiveTransactionsResponseSchema,
  ProcessedTransactionsResponseSchema,
  TransactionAuditResponseSchema,
  type ActiveTransactionsResponse,
  type ProcessedTransactionsResponse,
  type TransactionAuditResponse,
} from "@/types/schemas";
import { getComponentLogger } from "@/lib/logger";

const log = getComponentLogger("api");

// Server-side BFF fetches go through the Next.js rewrite (next.config.ts), which
// forwards /api/* to INTERNAL_API_URL inside the Docker bridge network. Using a
// relative base means both browser and SSR paths hit the Next.js proxy correctly.
const BFF_BASE = "";

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

// ---------------------------------------------------------------------------
// SSE stream URL (consumed directly via native EventSource in components)
// ---------------------------------------------------------------------------

export function getSseStreamUrl(): string {
  return `${SSE_BASE}/api/v1/stream`;
}
