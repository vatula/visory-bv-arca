import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueuePanel } from "@/components/QueuePanel";
import { type QueuedTransaction } from "@/types/schemas";

const tx1: QueuedTransaction = {
  transaction_id: "tx_q_001",
  date: "2026-01-15",
  description: "AWS Cloud Services",
  amount: -450.0,
  currency: "AUD",
  type: "DEBIT",
  bank_account_id: "acc_001",
};

const tx2: QueuedTransaction = {
  transaction_id: "tx_q_002",
  date: "2026-01-16",
  description: "Office Supplies",
  amount: -120.5,
  currency: "AUD",
  type: "DEBIT",
  bank_account_id: null,
};

describe("QueuePanel", () => {
  it("renders 'Up Next' heading", () => {
    render(<QueuePanel queue={[]} totalRemaining={0} />);
    expect(screen.getByText("Up Next")).toBeDefined();
  });

  it("renders totalRemaining badge", () => {
    render(<QueuePanel queue={[]} totalRemaining={42} />);
    expect(screen.getByText("42 remaining")).toBeDefined();
  });

  it("renders 'Queue empty' when queue is empty", () => {
    render(<QueuePanel queue={[]} totalRemaining={0} />);
    expect(screen.getByText("Queue empty")).toBeDefined();
  });

  it("does not render 'Queue empty' when queue has items", () => {
    render(<QueuePanel queue={[tx1]} totalRemaining={1} />);
    expect(screen.queryByText("Queue empty")).toBeNull();
  });

  it("renders item description", () => {
    render(<QueuePanel queue={[tx1]} totalRemaining={1} />);
    expect(screen.getByText("AWS Cloud Services")).toBeDefined();
  });

  it("renders formatted amount with currency using absolute value", () => {
    render(<QueuePanel queue={[tx1]} totalRemaining={1} />);
    expect(screen.getByText("AUD 450.00")).toBeDefined();
  });

  it("renders item date", () => {
    render(<QueuePanel queue={[tx1]} totalRemaining={1} />);
    expect(screen.getByText("2026-01-15")).toBeDefined();
  });

  it("renders position index starting at 1", () => {
    render(<QueuePanel queue={[tx1, tx2]} totalRemaining={2} />);
    expect(screen.getByText("1")).toBeDefined();
    expect(screen.getByText("2")).toBeDefined();
  });

  it("renders multiple items", () => {
    render(<QueuePanel queue={[tx1, tx2]} totalRemaining={2} />);
    expect(screen.getByText("AWS Cloud Services")).toBeDefined();
    expect(screen.getByText("Office Supplies")).toBeDefined();
  });

  it("renders ordered list when queue is non-empty", () => {
    const { container } = render(<QueuePanel queue={[tx1]} totalRemaining={1} />);
    expect(container.querySelector("ol")).not.toBeNull();
  });

  it("does not render ordered list when queue is empty", () => {
    const { container } = render(<QueuePanel queue={[]} totalRemaining={0} />);
    expect(container.querySelector("ol")).toBeNull();
  });

  it("renders 0 remaining badge correctly", () => {
    render(<QueuePanel queue={[]} totalRemaining={0} />);
    expect(screen.getByText("0 remaining")).toBeDefined();
  });
});
