import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("@/lib/logger", () => ({
  getComponentLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  fetchActiveTransactions: vi.fn(),
  fetchProcessedTransactions: vi.fn(),
  fetchQueue: vi.fn(),
  submitTransaction: vi.fn(),
  resetState: vi.fn(),
  getSseStreamUrl: vi.fn(() => "http://localhost:8000/api/v1/stream"),
}));

import * as api from "@/lib/api";
import DashboardPage from "@/app/dashboard/page";

// ---------------------------------------------------------------------------
// Mock EventSource — prevents real SSE connections in jsdom
// ---------------------------------------------------------------------------

class MockEventSource {
  url: string;
  onerror: ((e: Event) => void) | null = null;
  private readonly listeners = new Map<string, Array<(e: MessageEvent) => void>>();

  constructor(url: string) {
    this.url = url;
  }

  addEventListener(type: string, listener: (e: MessageEvent) => void): void {
    const existing = this.listeners.get(type) ?? [];
    this.listeners.set(type, [...existing, listener]);
  }

  close(): void {}
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockQueueFull = {
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
  total_remaining: 10,
};

const mockQueueEmpty = { queue: [], total_remaining: 0 };
const mockActive = { active: [] };
const mockProcessed = { processed: [] };

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("DashboardPage", () => {
  const mockResetResponse = {
    message: "Application state reset successfully.",
    rows_deleted_ui_read_model: 52,
    rows_deleted_audit_events: 104,
  };

  beforeEach(() => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.mocked(api.fetchActiveTransactions).mockResolvedValue(mockActive);
    vi.mocked(api.fetchProcessedTransactions).mockResolvedValue(mockProcessed);
    vi.mocked(api.fetchQueue).mockResolvedValue(mockQueueFull);
    vi.mocked(api.submitTransaction).mockResolvedValue(undefined);
    vi.mocked(api.resetState).mockResolvedValue(mockResetResponse);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  // -------------------------------------------------------------------------
  // Loading / error states
  // -------------------------------------------------------------------------

  it("renders loading state before data arrives", () => {
    vi.mocked(api.fetchActiveTransactions).mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    expect(screen.getByText("Loading dashboard…")).toBeDefined();
  });

  it("renders error message when initial load fails", async () => {
    vi.mocked(api.fetchActiveTransactions).mockRejectedValue(new Error("fetch failed"));
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Failed to load transactions.")).toBeDefined();
    });
  });

  // -------------------------------------------------------------------------
  // Ready state
  // -------------------------------------------------------------------------

  it("renders ARCRA Dashboard heading after successful load", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("ARCRA Dashboard")).toBeDefined();
    });
  });

  it("calls fetchActiveTransactions, fetchProcessedTransactions, fetchQueue on mount", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(api.fetchActiveTransactions).toHaveBeenCalledTimes(1);
      expect(api.fetchProcessedTransactions).toHaveBeenCalledTimes(1);
      expect(api.fetchQueue).toHaveBeenCalledTimes(1);
    });
  });

  it("renders queue items from fetchQueue in QueuePanel", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("AWS Cloud Services")).toBeDefined();
    });
  });

  // -------------------------------------------------------------------------
  // Play / Pause button state
  // -------------------------------------------------------------------------

  it("renders Play button in ready state", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Play")).toBeDefined();
    });
  });

  it("Play button is enabled when queue has items", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      const btn = screen.getByRole("button");
      expect((btn as HTMLButtonElement).disabled).toBe(false);
    });
  });

  it("shows Reset button when queue is empty even if active transactions still exist", async () => {
    vi.mocked(api.fetchQueue).mockResolvedValue(mockQueueEmpty);
    vi.mocked(api.fetchActiveTransactions).mockResolvedValue({
      active: [
        {
          transaction_id: "tx_active_999",
          status: "awaiting_slack" as const,
          amount: 50,
          merchant: "IN-FLIGHT CORP",
          employee_name: null,
          confidence_score: null,
          synthesis_reasoning: null,
          last_updated: "2026-03-23T00:00:00.000000+00:00",
        },
      ],
    });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Reset")).toBeDefined();
    });
  });

  it("toggles to Pause label when Play is clicked", async () => {
    // submitTransaction never resolves so the loop stays in-flight
    vi.mocked(api.submitTransaction).mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Play")).toBeDefined();
    });
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Pause")).toBeDefined();
  });

  it("toggles back to Play label when Pause is clicked", async () => {
    vi.mocked(api.submitTransaction).mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Play")).toBeDefined();
    });
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Pause")).toBeDefined();
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Play")).toBeDefined();
  });

  // -------------------------------------------------------------------------
  // Processing loop behaviour
  // -------------------------------------------------------------------------

  it("calls submitTransaction with the first queued item when Play is clicked", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Play")).toBeDefined();
    });
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(api.submitTransaction).toHaveBeenCalledWith(
        expect.objectContaining({ transaction_id: "tx_001" }),
      );
    });
  });

  it("re-fetches queue after a transaction is processed", async () => {
    // Return empty queue after the initial fetch so the processing loop
    // terminates after one transaction instead of running indefinitely.
    vi.mocked(api.fetchQueue)
      .mockResolvedValueOnce(mockQueueFull)
      .mockResolvedValue(mockQueueEmpty);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Play")).toBeDefined();
    });
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      // Call 1: initial mount. Call 2: refreshAll after transaction processed.
      expect(api.fetchQueue).toHaveBeenCalledTimes(2);
    });
  });

  it("does not call submitTransaction when isPlaying is false", async () => {
    // Ensure loop from any prior test cannot bleed in: empty queue after first fetch.
    vi.mocked(api.fetchQueue)
      .mockResolvedValueOnce(mockQueueFull)
      .mockResolvedValue(mockQueueEmpty);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Play")).toBeDefined();
    });
    // Do NOT click Play — assert submitTransaction was never called
    expect(api.submitTransaction).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  // Reset button visibility and behaviour
  // -------------------------------------------------------------------------

  it("does not render Reset button when queue has items", async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Play")).toBeDefined();
    });
    expect(screen.queryByText("Reset")).toBeNull();
  });

  it("renders Reset button when queue is empty and no active transactions", async () => {
    vi.mocked(api.fetchQueue).mockResolvedValue(mockQueueEmpty);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Reset")).toBeDefined();
    });
  });

  it("renders Reset button when queue is empty and active transactions exist (awaiting_slack stuck state)", async () => {
    vi.mocked(api.fetchQueue).mockResolvedValue(mockQueueEmpty);
    vi.mocked(api.fetchActiveTransactions).mockResolvedValue({
      active: [
        {
          transaction_id: "tx_active_001",
          status: "awaiting_slack" as const,
          amount: 100,
          merchant: "ACME",
          employee_name: null,
          confidence_score: null,
          synthesis_reasoning: null,
          last_updated: "2026-03-22T12:00:00.000000+00:00",
        },
      ],
    });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Reset")).toBeDefined();
    });
  });

  it("calls resetState when Reset button is clicked", async () => {
    vi.mocked(api.fetchQueue)
      .mockResolvedValueOnce(mockQueueEmpty)
      .mockResolvedValue(mockQueueEmpty);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Reset")).toBeDefined();
    });
    fireEvent.click(screen.getByText("Reset"));
    await waitFor(() => {
      expect(api.resetState).toHaveBeenCalledTimes(1);
    });
  });

  it("re-fetches all panels after Reset is clicked", async () => {
    vi.mocked(api.fetchQueue)
      .mockResolvedValueOnce(mockQueueEmpty)
      .mockResolvedValue(mockQueueFull);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Reset")).toBeDefined();
    });
    fireEvent.click(screen.getByText("Reset"));
    await waitFor(() => {
      // Call 1: initial mount. Call 2: refreshAll after reset.
      expect(api.fetchQueue).toHaveBeenCalledTimes(2);
    });
  });
});
