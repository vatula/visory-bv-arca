"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import {
  fetchActiveTransactions,
  fetchProcessedTransactions,
  fetchQueue,
  getSseStreamUrl,
  resetState,
  submitTransaction,
} from "@/lib/api";
import { getComponentLogger } from "@/lib/logger";
import {
  ActiveTransactionsResponseSchema,
  ProcessedTransactionsResponseSchema,
  type DashboardState,
  type TransactionSummary,
} from "@/types/schemas";

const log = getComponentLogger("DashboardPage");

export default function DashboardPage(): React.JSX.Element {
  const [state, setState] = useState<DashboardState>({ kind: "loading" });
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const processingRef = useRef<boolean>(false);

  // ---------------------------------------------------------------------------
  // Initial load — active, processed, and queue in parallel
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;

    async function load(): Promise<void> {
      try {
        const [activeRes, processedRes, queueRes] = await Promise.all([
          fetchActiveTransactions(),
          fetchProcessedTransactions(),
          fetchQueue(),
        ]);
        if (cancelled) return;
        setState({
          kind: "ready",
          active: activeRes.active,
          processed: processedRes.processed,
          queue: queueRes.queue,
          totalRemaining: queueRes.total_remaining,
        });
        log.info(
          {
            active: activeRes.active.length,
            processed: processedRes.processed.length,
            queue: queueRes.queue.length,
            totalRemaining: queueRes.total_remaining,
          },
          "dashboard_loaded",
        );
      } catch (err) {
        if (cancelled) return;
        log.error({ err }, "dashboard_load_failed");
        setState({ kind: "error", message: "Failed to load transactions." });
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  // ---------------------------------------------------------------------------
  // SSE stream — live push of active/processed updates
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const url = getSseStreamUrl();
    const es = new EventSource(url);

    es.addEventListener("active_update", (ev: MessageEvent) => {
      try {
        const raw: unknown = JSON.parse(ev.data as string);
        const parsed = ActiveTransactionsResponseSchema.safeParse(raw);
        if (parsed.success) {
          setState((prev) =>
            prev.kind === "ready"
              ? { ...prev, active: parsed.data.active }
              : prev,
          );
        }
      } catch (err) {
        log.warn({ err }, "sse_active_parse_failed");
      }
    });

    es.addEventListener("processed_update", (ev: MessageEvent) => {
      try {
        const raw: unknown = JSON.parse(ev.data as string);
        const parsed = ProcessedTransactionsResponseSchema.safeParse(raw);
        if (parsed.success) {
          setState((prev) =>
            prev.kind === "ready"
              ? { ...prev, processed: parsed.data.processed }
              : prev,
          );
        }
      } catch (err) {
        log.warn({ err }, "sse_processed_parse_failed");
      }
    });

    es.onerror = () => {
      log.warn({ url }, "sse_connection_error");
    };

    return () => {
      es.close();
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Refresh helper — re-fetches all three panels
  // ---------------------------------------------------------------------------
  const refreshAll = useCallback(async (): Promise<void> => {
    const [activeRes, processedRes, queueRes] = await Promise.all([
      fetchActiveTransactions(),
      fetchProcessedTransactions(),
      fetchQueue(),
    ]);
    setState((prev) =>
      prev.kind === "ready"
        ? {
            ...prev,
            active: activeRes.active,
            processed: processedRes.processed,
            queue: queueRes.queue,
            totalRemaining: queueRes.total_remaining,
          }
        : prev,
    );
  }, []);

  // ---------------------------------------------------------------------------
  // Sequential processing loop — fires when isPlaying is true
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!isPlaying) return;
    if (state.kind !== "ready") return;
    if (state.queue.length === 0) {
      log.info({}, "processing_queue_empty");
      setIsPlaying(false);
      return;
    }
    if (processingRef.current) return;

    let cancelled = false;
    processingRef.current = true;

    const next = state.queue[0];

    async function processNext(): Promise<void> {
      if (!next) return;
      log.info({ transaction_id: next.transaction_id }, "processing_next");
      try {
        await submitTransaction(next);
        if (cancelled) return;
        await refreshAll();
      } catch (err) {
        if (cancelled) return;
        log.error({ err, transaction_id: next.transaction_id }, "processing_loop_error");
      } finally {
        if (!cancelled) {
          processingRef.current = false;
        }
      }
    }

    void processNext();

    return () => {
      cancelled = true;
      processingRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, state]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  if (state.kind === "loading") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="animate-pulse text-sm text-gray-500">Loading dashboard…</p>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-sm text-red-400">{state.message}</p>
      </div>
    );
  }

  const queueEmpty = state.queue.length === 0 && state.totalRemaining === 0;
  const canReset = queueEmpty && !isPlaying;

  const handleReset = async (): Promise<void> => {
    setIsResetting(true);
    try {
      await resetState();
      log.info({}, "state_reset_triggered");
      await refreshAll();
    } catch (err) {
      log.error({ err }, "state_reset_failed");
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header bar with Play/Pause control */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">ARCRA Dashboard</h1>
          <p className="mt-0.5 text-xs text-gray-500">
            Autonomous Reconciliation &amp; Contextual Resolution Agent
          </p>
        </div>
        <div className="flex items-center gap-2">
          {canReset ? (
            <button
              onClick={() => void handleReset()}
              disabled={isResetting}
              className="flex items-center gap-2 rounded-lg bg-gray-700 px-4 py-2 text-sm font-semibold text-gray-200 transition-colors hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-950 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <span aria-hidden="true">↺</span>
              {isResetting ? "Resetting…" : "Reset"}
            </button>
          ) : (
            <button
              onClick={() => setIsPlaying((p) => !p)}
              disabled={queueEmpty}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-950 disabled:cursor-not-allowed disabled:opacity-40 ${
                isPlaying
                  ? "bg-amber-600 text-white hover:bg-amber-700 focus:ring-amber-500"
                  : "bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-500"
              }`}
            >
              {isPlaying ? (
                <>
                  <span aria-hidden="true">⏸</span> Pause
                </>
              ) : (
                <>
                  <span aria-hidden="true">▶</span> Play
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Main dashboard layout — queue + active + processed */}
      <DashboardLayout
        active={state.active as TransactionSummary[]}
        processed={state.processed as TransactionSummary[]}
        queue={state.queue}
        totalRemaining={state.totalRemaining}
      />
    </div>
  );
}
