# Prototype: Autonomous Reconciliation and Contextual Resolution Agent (ARCRA)

## Strategic Product Thinking and Gap Identification

The target application selected for this blueprint is Xero, 
the dominant cloud accounting platform in the Australian market.

While Xero has recently announced "JAX" (Just Done with your control), an AI superagent designed to automate routine tasks, 
critical analysis of the current accounting software landscape reveals a glaring functional void.

Current tools are proficient at processing perfectly formatted data, 
but they fail entirely when confronted with unstructured ambiguity. 
The most persistent, time-consuming bottleneck in financial operations 
is the asynchronous chase for missing context.

When a transaction appears on a _corporate card feed_ lacking a _receipt_, 
or when _an invoice description_ is _too vague_ to determine the correct _general ledger (GL) code_, 
the automation halts. A human bookkeeper must transition across multiple applications--
searching email inboxes, 
querying corporate knowledge bases like Notion for expense policies, 
and pinging employees on Slack—to piece together the narrative of the expense. 
The missing feature is a system capable of executing this multi-system traversal autonomously.

The proposed prototype is the **Autonomous Reconciliation and Contextual Resolution Agent (ARCRA)**. 
ARCRA is an agentic workflow orchestration engine, powered by MCP, 
that detects anomalies in the Xero ledger and autonomously navigates external enterprise 
tools to gather context, resolve ambiguity, and prepare the transaction for final human approval.

## Storyboarding the Agentic User Experience

ARCRA is designed to elevate human accountants to the role of an auditor and final decision-maker, 
aligning with the concept of verifiable, accountable intelligence.

The workflow is initiated when the system ingests a batch of daily bank feed transactions. 
The logic engine flags a specific entry: a $4,500 debit to "Acme Cloud Services" 
executed by an employee named Alice, which lacks a matching invoice in the system.

1. **Anomaly Detection and Orchestration Initiation:** ARCRA identifies the un-reconciled transaction. The central Python-based orchestrator, powered by an advanced reasoning model, formulates a multi-step resolution plan.
2. **Policy Verification:** The agent determines it must first understand the organizational rules regarding software expenditures. It invokes a locally hosted Notion MCP Server, executing a semantic search query against the corporate wiki for "IT Procurement Policy and Expense Limits". The server returns the policy, which states that cloud expenses over $2,000 require a specific project code.
3. **Document Retrieval:** Understanding that the invoice might have been auto-saved but not uploaded to the accounting software, ARCRA invokes the Google Drive MCP Server. It uses the searchFiles tool to look for PDF documents containing the string "Acme Cloud Services" modified within the last seven days. In this scenario, the search yields no results.
4. **Asynchronous Intervention:** Failing to find the documentation autonomously, ARCRA recognizes that it must interface with a human. It queries the Xero contact database to identify the Slack handle associated with the corporate cardholder. ARCRA then invokes the Slack MCP Server to send a direct, contextualized message: "Hi Alice, I am attempting to reconcile a $4,500 charge to Acme Cloud on your corporate card from Tuesday. I could not locate the invoice in the shared drive, and per company policy, this requires a project code. Could you please reply with the invoice and the relevant code?".
5. **Stateful Suspension and Resumption:** The agentic loop enters a suspended state, awaiting external input without consuming active compute resources.
6. **Context Synthesis and Xero Ledger Update:** Upon receiving a reply from Alice containing the PDF and the text "Project Phoenix," ARCRA resumes. It utilizes an internal vision model to extract the line items from the PDF. It then invokes the Xero MCP Server, utilizing the `createDraftInvoice` tool to generate a fully populated, coded draft bill in the accounting system, attaching the PDF as supporting evidence.
7. **Human Validation:** The human bookkeeper logs into the Visory platform dashboard, reviews the drafted entry alongside the full audit trail of ARCRA's investigation, and clicks "Approve".

## Technical Architecture and Execution Strategy

The architecture relies on a hybrid stack that 
leverages the strongest attributes of both Python and TypeScript.

The system is decoupled into four primary layers: the Orchestration Engine, the Observability Pipeline, the Agentic Observability Console, and the MCP Service Mesh.

1. **The Orchestration Engine (Python — `pydantic_graph` + FastAPI):** The agentic workflow is modelled as a set of four composable Finite State Machine (FSM) sub-graphs using `pydantic_graph`: `AnomalyGraph` (ledger variance detection), `PolicyGraph` (Notion policy retrieval), `GatheringGraph` (Drive and Slack evidence collection), and `SynthesisGraph` (confidence scoring and Xero draft creation). These are stateful, cyclic graphs — not directed acyclic graphs — because `GatheringGraph` natively suspends execution via `interrupt()` while awaiting a Slack webhook reply, persisting the full graph state to a SQLite checkpoint (`arcra_checkpoints`) so that compute is released during the wait. LLM inference within nodes is performed via `pydantic-ai`'s `BedrockModel` (AWS Bedrock). A FastAPI application acts as the strict API boundary, exposing the SQLite Read Model to the frontend via an OpenAPI 3.0 specification and receiving the inbound Slack webhook to resume a suspended graph thread.
2. **The Dual-Stream Observability Pipeline (`structlog` + SQLite CQRS):** Graph nodes never write to the database directly. Instead, they emit structured `structlog` events flagged with `is_telemetry=True`. A custom `structlog` processor forks every event into two streams: Stream 1 forwards all events to `stdout` (console renderer in development, JSON renderer in production); Stream 2 intercepts telemetry-flagged events and writes them into a SQLite CQRS Read Model composed of two tables — `arcra_ui_read_model` (one row per transaction, tracking current status and confidence score) and `arcra_audit_events` (a chronological append-only audit trail of every node traversal, including Slack messages sent and replies received).
3. **The Agentic Observability Console (TypeScript — Next.js):** The frontend is a Next.js application using the Backend-for-Frontend (BFF) pattern. Next.js Server Components fetch data from the Python backend over the internal Docker bridge network (`INTERNAL_API_URL`), so the backend is never exposed directly to the browser. The dashboard is divided into an Active Execution Queue (transactions currently traversing the graph, with suspended states highlighted) and a Processed Ledger (terminal resolved or escalated states). Clicking a transaction opens a deep-dive audit view rendering the full `AuditTimeline`, a `SlackInteractionViewer` component, and the Bedrock agent's synthesis reasoning with a visual confidence score.
4. **The MCP Service Mesh (TypeScript — Node.js):** The individual Model Context Protocol servers — for Notion (policy semantic search), Google Drive (invoice retrieval), Slack (asynchronous human intervention), and Xero (draft bill creation) — are implemented in TypeScript. TypeScript is chosen for this execution layer because its robust static typing ensures that the JSON schemas defining the MCP tool contracts are mathematically rigorous, preventing the AI from generating malformed API payloads.
