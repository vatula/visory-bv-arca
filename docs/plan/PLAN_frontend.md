# ARCRA Frontend: Agentic Observability Console

## Core Architecture

 - **Framework:** Next.js (TypeScript) acting as the Frontend Server. This allows for server-side API fetching (BFF pattern) so the internal Python backend is never exposed to the client browser.
 - **Styling:** Tailwind CSS for a high-density, data-rich auditing interface.
 - **Communication:** RESTful fetching against the backend's OpenAPI 3.0 specification.

## Dashboard Layout (The "Line URL")

The main view is divided into three distinct operational zones to accurately reflect the agentic state machine:

### 1. The Active Execution Queue (Max 10)

Displays transactions currently traversing the Pydantic Graph.

 - **Pending:** Ingested, awaiting anomaly detection.
 - **Suspended (Highlighted):** Graph interrupted. Waiting on a human (e.g., "Awaiting Slack reply from @alice").

### 2. The Processed Ledger (Max 10)

Displays terminal states from the Synthesis Graph.

 - **Resolved:** High confidence, drafted to Xero.
 - **Escalated:** Low confidence or 48hr timeout. Requires manual intervention.

## The Audit Deep-Dive View

Clicking a processed/suspended transaction opens a detailed modal or dedicated route.

### 1. Transaction Ground Truth

 - Raw ledger data (Date, Amount, Merchant, Corporate Cardholder).

### 2. The Agentic Audit Trail (Chronological)

A visually distinct timeline of graph node traversals.

 - Timestamp | Node: PolicyGraph | Action: Extracted "Cloud software requires project code" from Notion.
 - Timestamp | Node: GatheringGraph | Action: Drive search returned 0 results.
 - **The Slack Interaction Box:** A distinct UI component showing the exact Slack message sent, the target channel/user, and the payload received via the webhook.

### 3. Synthesis & Evaluation

 - **Confidence Score:** Displayed visually (e.g., progress bar or color-coded metric).
 - **Agent Reasoning:** The raw string output from the Bedrock evaluation detailing why it matched the receipt to the policy.