# Tasks: Evidence Gathering FSM

- [ ] **Node Implementation (`CheckDriveNode`):** Use the Drive MCP to search for file names. If found, append to `evidence_documents` in the state object and route directly to `SynthesisGraph`.
- [ ] **Node Implementation (`DispatchSlackNode`):** If Drive is missing evidence, query the Xero contact DB for the Slack handle. Dispatch a message via Slack MCP. Record the `slack_message_ts` in the `arcra_interrupts` table.
- [ ] **Node Implementation (`InterruptGraphNode`):** Execute a native graph `interrupt()` (or raise a `NodeInterrupt`). This completely halts execution and serializes the current state to the `arcra_checkpoints` table.
- [ ] **Webhook Implementation (`FastAPI`):** Create an endpoint `/webhook/slack`. When a user replies, look up the `thread_id` using the Slack timestamp, extract the payload (e.g., file buffer/text), and call `graph.resume(thread_id, payload)`.
- [ ] **Node Implementation (`NormalizeToDriveNode`):** (Executes immediately upon graph resumption). Take the injected webhook payload, upload the file to Drive MCP, and append the new URI to the state's `evidence_documents`. Route to `SynthesisGraph`.
- [ ] **Timeout Cron:** Implement a simple background script that runs hourly, checks `arcra_interrupts` for expired timestamps, and forcefully resumes the graph with a `timeout_error` payload, routing it to human review.