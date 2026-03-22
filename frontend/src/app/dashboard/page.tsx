"use client";

import { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { fetchActiveTransactions, fetchProcessedTransactions, getSseStreamUrl } from "@/lib/api";
import { TransactionSummarySchema, type DashboardState, type TransactionSummary } from "@/types/schemas";
import { getComponentLogger } from "@/lib/logger";

const log = getComponentLogger("DashboardPage");

export default function DashboardPage(): React.JSX.Element {
  const [state, setState] = useState<DashboardState>({ kind: "loading" });

  // Initial data fetch
  useEffect(() => {
    let cancelled = false;

    async function loadInitial(): Promise<void> {
      try {
        const [activeRes, processedRes] = await Promise.all([
          fetchActiveTransactions(),
          fetchProcessedTransactions(),
        ]);
        if (!cancelled) {
          setState({
            kind: "ready",
            active: activeRes.active,
            processed: processedRes.processed,
          });
          log.info({ activeCount: activeRes.active.length, processedCount: processedRes.processed.length }, "dashboard_initial_load");
        }
      } catch (err) {
        if (!cancelled) {
          log.error({ err }, "dashboard_initial_load_failed");
          setState({ kind: "error", message: "Failed to load transactions." });
        }
      }
    }

    void loadInitial();
    return () => { cancelled = true; };
  }, []);

  // SSE stream — PLAN_OVERRIDE #4: native EventSource in useEffect
  useEffect(() => {
    const url = getSseStreamUrl();
    log.info({ url }, "sse_connecting");

    const es = new EventSource(url);

    es.onopen = () => {
      log.info({ url }, "sse_connected");
    };

    es.onmessage = (ev: MessageEvent<string>) => {
      let raw: unknown;
      try {
        raw = JSON.parse(ev.data) as unknown;
      } catch (err) {
        log.warn({ err, data: ev.data }, "sse_json_parse_failed");
        return;
      }

      // Expect: { type: "active_update"|"processed_update", data: TransactionSummary }
      if (
        raw !== null &&
        typeof raw === "object" &&
        "type" in raw &&
        "data" in raw
      ) {
        const payload = raw as { type: string; data: unknown };
        const parsed = TransactionSummarySchema.safeParse(payload.data);
        if (!parsed.success) {
          log.warn({ issues: parsed.error.issues }, "sse_payload_schema_invalid");
          return;
        }
        const updated: TransactionSummary = parsed.data;

        setState((prev) => {
          if (prev.kind !== "ready") return prev;

          if (payload.type === "active_update") {
            const exists = prev.active.some(
              (t) => t.transaction_id === updated.transaction_id,
            );
            const next = exists
              ? prev.active.map((t) =>
                  t.transaction_id === updated.transaction_id ? updated : t,
                )
              : [updated, ...prev.active];
            log.debug({ transaction_id: updated.transaction_id }, "sse_active_update");
            return { ...prev, active: next };
          }

          if (payload.type === "processed_update") {
            // Remove from active if present, add/update in processed
            const nextActive = prev.active.filter(
              (t) => t.transaction_id !== updated.transaction_id,
            );
            const existsProcessed = prev.processed.some(
              (t) => t.transaction_id === updated.transaction_id,
            );
            const nextProcessed = existsProcessed
              ? prev.processed.map((t) =>
                  t.transaction_id === updated.transaction_id ? updated : t,
                )
              : [updated, ...prev.processed];
            log.debug({ transaction_id: updated.transaction_id }, "sse_processed_update");
            return { ...prev, active: nextActive, processed: nextProcessed };
          }

          return prev;
        });
      }
    };

    es.onerror = () => {
      log.warn({ url }, "sse_connection_error");
    };

    return () => {
      log.info({ url }, "sse_disconnecting");
      es.close();
    };
  }, []);

  // Render states
  if (state.kind === "loading") {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="text-sm text-gray-500">Loading transactions…</span>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-400">
        {state.message}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-lg font-bold text-white">Dashboard</h1>
        <span className="flex items-center gap-1.5 text-xs text-green-400">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-green-400" />
          Live
        </span>
      </div>
      <DashboardLayout active={state.active} processed={state.processed} />
    </div>
  );
}
