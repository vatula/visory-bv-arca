# ARCRA Architecture: 12-Hour Implementation Overrides

**ATTENTION AI CODING AGENT:** You are to implement the ARCRA architecture as defined in the `PLAN_*.md` files, but you **MUST** override the original instructions with the following mission-critical constraints. These overrides are designed to ensure deterministic execution, prevent SQLite deadlocks, and guarantee type safety.

## 1. Deterministic LLM Guardrails (The "No Math" Rule)

LLMs cannot do reliable arithmetic. You must isolate logic into deterministic Python blocks.

* **Override for Anomaly & Policy Graphs:** Do **NOT** ask the Pydantic AI `BedrockModel` to evaluate numerical thresholds (e.g., "Is this over $500?").  
* **Implementation:** The `ArcraState` must have pure Python properties or standard Pydantic `@computed_field` validators that perform the mathematical comparisons based on the `xero_api_feed.json` data. The LLM's _only_ job is to extract text entities (e.g., "Extract the attendees list" or "Find the project code").

## 2. Telemetry & SQLite Concurrency

Do not attempt complex async `structlog` interception. We must protect the Python event loop and prevent SQLite locks.

* **Override for Database Init:** You **MUST** execute `PRAGMA journal_mode=WAL;` and `PRAGMA synchronous=NORMAL;` immediately upon establishing the SQLite connection. Use `aiosqlite` exclusively.  
* **Override for Telemetry Pipeline:** Instead of a complex `structlog` sink, implement a simple middleware or wrapper around the logger. If `is_telemetry=True`, dispatch the database insert using `asyncio.create_task(db.insert_audit_event(...))` so it runs in the background without blocking the FSM node execution.

## 3. Graph Suspension & Resumption (Simplification)

Native graph `interrupt()` is too brittle for this prototype.

* **Override for Gathering Graph:** When the system needs to wait for a Slack reply, the FSM should explicitly transition to a `SuspendForSlackNode`. This node saves the state to `arcra_checkpoints` with `status="awaiting_slack"` and then **terminates** the graph execution completely.  
* **Webhook Resume:** The FastAPI `/webhook/slack` endpoint will receive the payload, load the state from the DB, append the Slack reply to the state, and explicitly start a *new* graph execution run with the loaded state. Do not attempt in-memory thread resumption.

## 4. Next.js Frontend Reactivity (Server-Sent Events)

Do not use REST polling for the active queues.

* **Override for FastAPI:** Implement a simple Server-Sent Events (SSE) endpoint using FastAPI's `StreamingResponse` at `/api/v1/stream`. Have it monitor the `arcra_ui_read_model` SQLite table for changes (a simple 1-second sleep loop checking a `last_updated` timestamp is acceptable for this prototype).  
* **Override for Next.js:** Use the native browser `EventSource` API in a `useEffect` hook to listen to the SSE stream and dynamically update the React state for the `DashboardLayout`.

## 5. Resolving Task Contradictions

* **Clarification on `tasks_telemetry.md`:** Ignore the directive to "emit an event to insert a row" manually at the end of every node. Stick strictly to the CQRS rule: Nodes are pure. They only call `logger.info(..., is_telemetry=True)`. The background task wrapper (defined in Override \#2) handles the DB insert.  
* **Context Window Truncation:** When reading from `resources/policies/*.md`, do not pass the entire file to the LLM. You must use a deterministic Python string search (e.g., `if "travel" in transaction.description.lower(): load travel.md`) to route only the relevant policy file to the prompt context.