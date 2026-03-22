# Tasks: Frontend Implementation (Next.js + Tailwind)

 - [ ] **Setup:** Initialize Next.js project with TypeScript and Tailwind CSS.
 - [ ] **Type Generation:** Generate TypeScript interfaces directly from the Python backend's `openapi.json` to guarantee type safety across the network boundary.
 - [ ] **Component (`DashboardLayout`):** Build a responsive grid with two main columns: "Active Operations" and "Recent Processing".
 - [ ] **Component (`TransactionCard`):** Design a dense data card showing Merchant, Amount, and a status badge (color-coded for Pending, Suspended, Resolved, Escalated).
 - [ ] **Route (`/transactions/[id]`):** Implement the Audit Deep-Dive page.
 - [ ] **Component (`AuditTimeline`):** Build a vertical timeline component. Map the array of `arcra_audit_events` to visual nodes.
 - [ ] **Component (`SlackInteractionViewer`):** Build a stylized component resembling a chat interface to clearly display the `slack_message_sent` and `slack_reply_received` strings.
 - [ ] **Component (`SynthesisMetrics`):** Visualize the Bedrock `confidence_score` and `synthesis_reasoning` text block.