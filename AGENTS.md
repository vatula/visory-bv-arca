# Coding rules

## Generic Architecture & Systems Thinking
- Isolate pure logic from side effects. Core transformations must be pure functions to ensure deterministic testing.
- Never swallow exceptions silently. Always log the error with context or re-raise a custom domain-specific exception.
- Use dependency injection for external services (APIs, databases, LLMs) to allow for reliable mocking during testing.
- Write tests that verify system behavior and edge cases, not just line coverage. 

## Python
- Ensure all imports are at the top of the file. NEVER import modules within functions.
- Always use `f-strings` for string formatting. Do not use `str.format`.
- Always inherit from `pydantic` `BaseModel` for data models except for (Hierarchical) Finite State Machine (FSM) models. Do not use `dataclasses`.
- Use Pydantic V2 syntax: Always use `@field_validator` or `@model_validator` for data validation. Do not leave model validation to the database.
- Always use `pydantic_graph` when modeling (H)FSMs. Do not write your own (H)FSM implementation.
- Always inherit from `pydantic_graph` `BaseNode` when modeling FSM states (nodes). Do not use standard `pydantic` `BaseModel` for nodes.
- **FSM Dependency Injection:** Always define a formal dependency model for FSM execution context.
- **FSM Context Passing:** Inject dependencies into `pydantic_graph` nodes strictly via the `run` method signature using `ctx: GraphRunContext[YourDepsModel]`. 
- **FSM Anti-Patterns:** Never inject dependencies via the `__init__` method of a `BaseNode`, and never rely on global variables for external services within an FSM.
- Enforce strict typing. Avoid `typing.Any`; use Generics (`TypeVar`) or `object` for unknown payloads before validation.
- Always check code with `mypy --strict`. Do not continue until all errors are fixed.
- Always use `pytest` for testing. Do not use `unittest`.
- Always use `pytest-cov` for code coverage. Do not use `coverage`.
- Always use `pytest-asyncio` for async testing. Do not use `asyncio`.
- Always use `fastapi` for API development. Do not use `flask`.

### Observability & Logging (Python)
- **Absolute Ban on `print()`:** Never use `print()`, `sys.stdout.write`, or `sys.stderr.write`. 
- **Mandate Structured Logging:** Always use the project's configured structured logger (`structlog` package). Logs must be emitted as JSON, not concatenated strings.
- **Context Binding:** Do not embed variables into log messages. Bind them as contextual kwargs (e.g., `logger.info("fsm_transition", from_state=state_a, to_state=state_b)`).
- **Strict Logging Levels (DEBUG):** Use exclusively for execution tracing. Include raw payloads, matrix dimensions, spatial coordinate bounds, or exact LLM prompt inputs. 
- **Strict Logging Levels (INFO):** Use for systemic lifecycle events only. Examples: service start/stop, completing a major pipeline stage, or FSM node transitions. Do not use for loop iterations.
- **Strict Logging Levels (WARNING):** Use for recoverable anomalies or threshold deviations. Examples: triggering a retry block, falling back to heuristic models when an LLM call fails, or encountering malformed but recoverable spatial geometries.
- **Strict Logging Levels (ERROR/EXCEPTION):** Use only for unrecoverable failures that halt the current unit of work. You must include the full stack trace (`exc_info=True`) and the state of the inputs at the time of failure.


## TypeScript
- Enable and adhere strictly to `tsconfig` `"strict": true`.
- Use `unknown` instead of `any` when a type is not yet known. Force type narrowing before usage.
- Always use `zod` for runtime data validation at system boundaries (e.g., API responses, inputs).
- Use Discriminated Unions to model complex states and Finite State Machines. 
- Always use exhaustive `switch` statements (using a `never` type check in the default case) when evaluating Discriminated Unions to ensure all states are handled.
- Prefer `readonly` properties and `ReadonlyArray` to enforce immutability by default.
- Use `vitest` for testing. 
- Avoid `class`-based inheritance for data models; prefer functional composition and interfaces.

### Observability & Logging (TypeScript)

- **Absolute Ban on `console` API:** Never use `console.log`, `console.info`, `console.warn`, or `console.error` anywhere in the codebase.
- **Mandate Universal `pino`:** Always use `pino` for logging across both Node.js (server) and browser (client) environments to maintain structural parity.
- **Context Binding:** Do not use string interpolation for variables in log messages. Always pass an object as the first argument to bind context (e.g., `logger.info({ userId, button }, "User interaction event")`).
- **Systemic Rule for Child Loggers:** Use `logger.child({ component: 'ComponentName', ...context })` at the initialization of complex classes, React components, or FSM instances to automatically append metadata to all subsequent logs in that scope.
- **Distributed Trace Injection:** Always initialize the root client-side logger and server-side logger with a shared `trace_id` to ensure deterministic cross-boundary tracking.
- **Client-Side Transport Awareness:** When configuring `pino` for the browser, never leave it defaulting to the browser console for production builds. Always configure a batching transport to ship logs to the backend telemetry ingestion endpoint.
- **Fatal Error Telemetry:** For unrecoverable client-side crashes, do not rely on standard batching. Ensure the transport utilizes `navigator.sendBeacon` or a synchronous flush to guarantee the error state is transmitted before the environment terminates.
- **Strict Logging Levels (debug):** Use for granular tracing. Include raw API payloads, state machine transition triggers, and intermediate calculation matrices.
- **Strict Logging Levels (info):** Use for systemic lifecycle events. Examples: component mount/unmount, successful auth token refresh, or completing a data fetch.
- **Strict Logging Levels (warn):** Use for recoverable anomalies. Examples: API timeouts triggering a retry mechanism, rendering fallbacks, or encountering unexpected but non-fatal data structures.
- **Strict Logging Levels (error/fatal):** Use strictly for unrecoverable state failures, uncaught boundary exceptions, or crashes. You must pass the native `Error` object to `pino` so it can serialize the stack trace: `logger.error({ err: errorObject }, "Description")`.


# ARCRA Agent Execution Protocol & Skill Mapping

## Directives for the AI Coding Agent

As the AI assisting in the implementation of the ARCRA prototype, you must adhere strictly to this protocol. This project relies on a highly decoupled architecture utilizing Pydantic Graphs, SQLite natively for state checkpointing, dual-stream structlog multiplexing, and a strict API boundary between the Python Backend and Next.js Frontend.

### **Your Operational Rules:**

1. **Context Window Strictness:** Before implementing any task, you must read its strictly bound `PLAN_*.md` document. Do not hallucinate architecture or database schemas.
2. **Task Tracking:** After completing a task, you must update the corresponding `docs/tasks/tasks_*.md` file, changing `[ ]` to `[x]`. If you discover missing intermediate steps during implementation, you must add them to the task list.
3. **Purity of the Graph:** Python execution nodes must remain mathematically pure. They do not execute database inserts for logging; they only emit state updates and `structlog` telemetry (`is_telemetry=True`).
4. **Data Grounding (No Mock Classes):** Do not write dummy python dictionaries for testing. You must use the files provided in the `resources/` directory (e.g., `xero_api_feed.json`, local policies) to hydrate your local graph tests.
5. **Strict Phase Gating:** **DO NOT** attempt to implement multiple phases at once. You must complete a phase, update its task list, output the code, and explicitly wait for the human to type "Proceed to Phase X" before continuing.

## Execution Order & Plan-to-Task Bindings

Implementation must proceed in the following ordered phases.

### Phase 1: Foundation & Observability Pipeline

Before the graph can run, the telemetry and state checkpointer must exist.

 - **Bound Plan:** `docs/plan/PLAN_telemetry.md`
 - **Bound Tasks:** `docs/tasks/tasks_telemetry.md`
 - **Required Skills Profile:** `docs/skills/skills_telemetry.md`
 - **Focus & Resources:** Implement the dual-stream multiplexer. Ensure the SQLite schema is initialized for both native graph checkpointing (`arcra_checkpoints`) and the UI Read Model (`arcra_ui_read_model`).

### Phase 2: Ingestion & Policy Extraction

The initial automated pathway.

**Processing policies**
 - **Bound Plans:** `docs/plan/PLAN_policy.md`
 - **Bound Tasks:** `docs/tasks/tasks_policy.md`
 - **Required Skills Profile:** `docs/skills/skills_policy.md`
 
**Processing anomalies**
 - **Bound Plans:** `docs/plan/PLAN_anomaly.md`
 - **Bound Tasks:** `docs/tasks/tasks_anomaly.md`
 - **Required Skills Profile:** `docs/skills/skills_anomaly.md`
 
**Focus & Resources:** Build the initial DAG nodes and hydrate the `ArcraState`. For local testing, ingest `resources/xero_api_feed.json`. For the Notion MCP simulation, read directly from `resources/policies/*.md`.


### Phase 3: Stateful Interruption (High Complexity)

The core scientific differentiator of ARCRA.

 - **Bound Plans:** `docs/plan/PLAN_gathering.md`
 - **Bound Tasks:** `docs/tasks/tasks_gathering.md`
 - **Required Skills Profile:** `docs/skills/skills_gathering.md`
 - **Focus & Resources:** Implement the native graph `interrupt()` when Slack is queried. Build the FastAPI endpoint `/webhook/slack` that catches the payload and resumes the graph via `thread_id`. For the Drive simulation, search against `resources/invoices/*.pdf` and `*.md`.

### Phase 4: Synthesis & Xero Draft

The final reasoning and output stage.

 - **Bound Plans:** `docs/plan/PLAN_synthesis.md`
 - **Bound Tasks:** `docs/tasks/tasks_synthesis.md`
 - **Required Skills Profile:** `docs/skills/skills_synthesis.md`
 - **Focus & Resources:** Merge the state context, evaluate the confidence score using Bedrock, and prepare the final ledger draft payload.

### Phase 5: The Agentic Observability Console

The decoupled frontend interface.

 - **Bound Plans:** `docs/plan/PLAN_frontend.md`
 - **Bound Tasks:** `docs/tasks/tasks_frontend.md`
 - **Required Skills Profile:** `docs/skills/skills_frontend.md`
 - **Focus & Resources:** Consume the FastAPI OpenAPI spec. Build the UI that reads from the `arcra_ui_read_model` and `arcra_audit_events` to visually display the agent's reasoning trace and interrupted states.

## Telemetry Implementation Note

When executing Phase 1 (Telemetry), refer strictly to the structlog multiplexer defined in the plan. Graph nodes must utilize: `logger.info("event", is_telemetry=True, ...)`. The interceptor must catch this flag, write to the SQLite `arcra_audit_events` table, and strip the flag before passing the event to `stdout`.

# General project tree structure

Broadly follow the following structure, ensuring `backend` is separated from `frontend` folder 
to avoid context blowout.

```text
<project_root>/
├── docs/                        # (Existing) Plans, tasks, and skills
├── resources/                   # (Existing) Local mock data, policies, invoices
├── AGENTS.md                    # (Existing) The master ruleset
├── pyproject.toml               # (Existing) Root Python definition (Optional: move to /backend)
│
├── backend/                     # -> PHASES 1, 2, 3, 4 (Python / FastAPI / Pydantic Graph)
│   ├── pyproject.toml           # Strict Python dependency boundary
│   ├── src/
│   │   ├── api/                 # FastAPI routes, webhooks, and OpenAPI spec generation
│   │   ├── core/                # structlog multiplexer, DB initialization, config
│   │   ├── graph/               # The Pydantic Graph: state definitions, nodes, transitions
│   │   └── services/            # Bedrock client, MCP client orchestration
│   └── tests/                   # pytest suite
│
├── frontend/                    # -> PHASE 5 (TypeScript / Next.js / Tailwind)
│   ├── package.json             # Strict UI dependency boundary
│   ├── tsconfig.json            # strict: true
│   ├── src/
│   │   ├── app/                 # Next.js App Router (pages, layouts)
│   │   ├── components/          # Reusable UI (AuditTimeline, StatusBadge)
│   │   ├── lib/                 # pino logger setup, generated OpenAPI client
│   │   └── types/               # Zod schemas, mapped types
│   └── tests/                   # vitest UI suite
│
└── mcp_servers/                 # -> (Future/Parallel) Node.js MCP Service Mesh
    ├── notion_mcp/              
    │   ├── package.json
    │   └── src/                 # Semantic search execution against local markdown
    ├── drive_mcp/
    └── slack_mcp/
```