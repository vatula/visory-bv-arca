import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { type QueuedTransaction, type TransactionSummary } from "@/types/schemas";

const baseTx: TransactionSummary = {
  transaction_id: "tx_100",
  status: "complete",
  amount: -890.0,
  merchant: "AWS",
  employee_name: "Alice",
  confidence_score: 0.92,
  synthesis_reasoning: "Matched cloud policy.",
  last_updated: "2026-01-15T10:00:00",
};

const activeTx: TransactionSummary = {
  transaction_id: "tx_200",
  status: "pending",
  amount: -200.0,
  merchant: "Stripe",
  employee_name: "Bob",
  confidence_score: null,
  synthesis_reasoning: null,
  last_updated: "2026-01-16T09:00:00",
};

const queuedTx: QueuedTransaction = {
  transaction_id: "tx_q_001",
  date: "2026-01-15",
  description: "Pending AWS charge",
  amount: -200.0,
  currency: "AUD",
  type: "DEBIT",
  bank_account_id: "acc_001",
};

const emptyProps = {
  active: [],
  processed: [],
  queue: [],
  totalRemaining: 0,
};

describe("DashboardLayout", () => {
  it("renders 'Active Operations' section heading", () => {
    render(<DashboardLayout {...emptyProps} />);
    expect(screen.getByText("Active Operations")).toBeDefined();
  });

  it("renders 'Processed Ledger' section heading", () => {
    render(<DashboardLayout {...emptyProps} />);
    expect(screen.getByText("Processed Ledger")).toBeDefined();
  });

  it("renders 'Up Next' queue heading via QueuePanel", () => {
    render(<DashboardLayout {...emptyProps} />);
    expect(screen.getByText("Up Next")).toBeDefined();
  });

  it("renders 'No active transactions' when active is empty", () => {
    render(<DashboardLayout {...emptyProps} />);
    expect(screen.getByText("No active transactions")).toBeDefined();
  });

  it("renders 'No processed transactions' when processed is empty", () => {
    render(<DashboardLayout {...emptyProps} />);
    expect(screen.getByText("No processed transactions")).toBeDefined();
  });

  it("renders 'Queue empty' via QueuePanel when queue is empty", () => {
    render(<DashboardLayout {...emptyProps} />);
    expect(screen.getByText("Queue empty")).toBeDefined();
  });

  it("renders active transaction merchant when active list is populated", () => {
    render(<DashboardLayout {...emptyProps} active={[baseTx]} />);
    expect(screen.getByText("AWS")).toBeDefined();
  });

  it("renders processed transaction merchant when processed list is populated", () => {
    render(<DashboardLayout {...emptyProps} processed={[baseTx]} />);
    expect(screen.getByText("AWS")).toBeDefined();
  });

  it("does not render 'No active transactions' when active list has items", () => {
    render(<DashboardLayout {...emptyProps} active={[activeTx]} />);
    expect(screen.queryByText("No active transactions")).toBeNull();
  });

  it("does not render 'No processed transactions' when processed list has items", () => {
    render(<DashboardLayout {...emptyProps} processed={[baseTx]} />);
    expect(screen.queryByText("No processed transactions")).toBeNull();
  });

  it("forwards queue items to QueuePanel", () => {
    render(
      <DashboardLayout
        {...emptyProps}
        queue={[queuedTx]}
        totalRemaining={1}
      />,
    );
    expect(screen.getByText("Pending AWS charge")).toBeDefined();
  });

  it("forwards totalRemaining to QueuePanel badge", () => {
    render(
      <DashboardLayout {...emptyProps} queue={[queuedTx]} totalRemaining={7} />,
    );
    expect(screen.getByText("7 remaining")).toBeDefined();
  });

  it("renders active and processed sections simultaneously", () => {
    render(
      <DashboardLayout
        {...emptyProps}
        active={[activeTx]}
        processed={[baseTx]}
      />,
    );
    expect(screen.getByText("Stripe")).toBeDefined();
    expect(screen.getByText("AWS")).toBeDefined();
  });
});
