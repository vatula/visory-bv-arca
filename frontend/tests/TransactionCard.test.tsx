import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TransactionCard } from "@/components/TransactionCard";
import { type TransactionSummary } from "@/types/schemas";

const baseTx: TransactionSummary = {
  transaction_id: "tx_100001",
  status: "complete",
  amount: -890.0,
  merchant: "AWS",
  employee_name: "Alice Johnson",
  confidence_score: 0.92,
  synthesis_reasoning: "Matched cloud policy.",
  last_updated: "2026-01-15T10:00:00",
};

describe("TransactionCard", () => {
  it("renders merchant name", () => {
    render(<TransactionCard transaction={baseTx} />);
    expect(screen.getByText("AWS")).toBeDefined();
  });

  it("renders employee name", () => {
    render(<TransactionCard transaction={baseTx} />);
    expect(screen.getByText("Alice Johnson")).toBeDefined();
  });

  it("renders formatted AUD amount", () => {
    render(<TransactionCard transaction={baseTx} />);
    expect(screen.getByText("-$890.00")).toBeDefined();
  });

  it("renders status badge", () => {
    render(<TransactionCard transaction={baseTx} />);
    expect(screen.getByText("Complete")).toBeDefined();
  });

  it("falls back to transaction_id when merchant is null", () => {
    render(<TransactionCard transaction={{ ...baseTx, merchant: null }} />);
    expect(screen.getByText("tx_100001")).toBeDefined();
  });

  it("does not render employee row when employee_name is null", () => {
    render(<TransactionCard transaction={{ ...baseTx, employee_name: null }} />);
    expect(screen.queryByText("Alice Johnson")).toBeNull();
  });

  it("renders em-dash for null amount", () => {
    render(<TransactionCard transaction={{ ...baseTx, amount: null }} />);
    expect(screen.getByText("—")).toBeDefined();
  });

  it("wraps content in a link to the transaction detail route", () => {
    const { container } = render(<TransactionCard transaction={baseTx} />);
    const anchor = container.querySelector("a");
    expect(anchor?.getAttribute("href")).toContain("tx_100001");
  });

  it("renders the awaiting_slack status with correct badge", () => {
    render(<TransactionCard transaction={{ ...baseTx, status: "awaiting_slack" }} />);
    expect(screen.getByText("Awaiting Slack")).toBeDefined();
  });
});
