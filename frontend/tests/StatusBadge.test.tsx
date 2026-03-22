import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "@/components/StatusBadge";
import { type TransactionStatus } from "@/types/schemas";

const cases: Array<[TransactionStatus, string]> = [
  ["pending", "Pending"],
  ["processing", "Processing"],
  ["policy_check", "Policy Check"],
  ["evidence_gathering", "Gathering Evidence"],
  ["awaiting_slack", "Awaiting Slack"],
  ["complete", "Complete"],
  ["escalated", "Escalated"],
];

describe("StatusBadge", () => {
  it.each(cases)("renders label '%s' → '%s'", (status, expectedLabel) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(expectedLabel)).toBeDefined();
  });

  it("applies a colour class for awaiting_slack", () => {
    const { container } = render(<StatusBadge status="awaiting_slack" />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("text-orange-300");
  });

  it("applies a colour class for escalated", () => {
    const { container } = render(<StatusBadge status="escalated" />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("text-red-300");
  });

  it("applies a colour class for complete", () => {
    const { container } = render(<StatusBadge status="complete" />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("text-green-300");
  });
});
