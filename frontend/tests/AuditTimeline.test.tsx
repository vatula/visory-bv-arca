import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuditTimeline } from "@/components/AuditTimeline";
import { type AuditEvent } from "@/types/schemas";

const baseEvent: AuditEvent = {
  id: 1,
  transaction_id: "tx_001",
  timestamp: "2026-01-15T10:00:00",
  node_name: "PolicyGraph",
  action_summary: "Extracted cloud rule from Notion.",
  slack_channel: null,
  slack_message_sent: null,
  slack_reply_received: null,
};

const slackEvent: AuditEvent = {
  id: 2,
  transaction_id: "tx_001",
  timestamp: "2026-01-15T10:05:00",
  node_name: "GatheringGraph",
  action_summary: "Drive search returned 0 results. Dispatching Slack query.",
  slack_channel: "finance",
  slack_message_sent: "Please provide receipt for AWS charge.",
  slack_reply_received: "Here is the receipt: inv_2026_001.",
};

describe("AuditTimeline", () => {
  it("renders empty state when no events", () => {
    render(<AuditTimeline events={[]} />);
    expect(screen.getByText("No audit events recorded.")).toBeDefined();
  });

  it("renders node name for each event", () => {
    render(<AuditTimeline events={[baseEvent]} />);
    expect(screen.getByText("PolicyGraph")).toBeDefined();
  });

  it("renders action summary for each event", () => {
    render(<AuditTimeline events={[baseEvent]} />);
    expect(screen.getByText("Extracted cloud rule from Notion.")).toBeDefined();
  });

  it("renders multiple events in order", () => {
    render(<AuditTimeline events={[baseEvent, slackEvent]} />);
    expect(screen.getByText("PolicyGraph")).toBeDefined();
    expect(screen.getByText("GatheringGraph")).toBeDefined();
  });

  it("renders SlackInteractionViewer when slack fields present", () => {
    render(<AuditTimeline events={[slackEvent]} />);
    expect(screen.getByText("Slack Interaction")).toBeDefined();
    expect(screen.getByText("#finance")).toBeDefined();
  });

  it("renders slack message sent", () => {
    render(<AuditTimeline events={[slackEvent]} />);
    expect(
      screen.getByText("Please provide receipt for AWS charge."),
    ).toBeDefined();
  });

  it("renders slack reply received", () => {
    render(<AuditTimeline events={[slackEvent]} />);
    expect(screen.getByText("Here is the receipt: inv_2026_001.")).toBeDefined();
  });

  it("does not render SlackInteractionViewer when slack fields are null", () => {
    render(<AuditTimeline events={[baseEvent]} />);
    expect(screen.queryByText("Slack Interaction")).toBeNull();
  });

  it("renders awaiting state when reply not yet received", () => {
    const pendingSlack: AuditEvent = {
      ...slackEvent,
      slack_reply_received: null,
    };
    render(<AuditTimeline events={[pendingSlack]} />);
    expect(screen.getByText("Awaiting reply…")).toBeDefined();
  });
});
