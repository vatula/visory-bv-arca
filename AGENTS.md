# AGENTS.md

## Coding rules

### Generic Architecture & Systems Thinking
- Isolate pure logic from side effects. Core transformations must be pure functions to ensure deterministic testing.
- Never swallow exceptions silently. Always log the error with context or re-raise a custom domain-specific exception.
- Use dependency injection for external services (APIs, databases, LLMs) to allow for reliable mocking during testing.
- Write tests that verify system behavior and edge cases, not just line coverage. 

### Python
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

#### Observability & Logging (Python)
- **Absolute Ban on `print()`:** Never use `print()`, `sys.stdout.write`, or `sys.stderr.write`. 
- **Mandate Structured Logging:** Always use the project's configured structured logger (`structlog` package). Logs must be emitted as JSON, not concatenated strings.
- **Context Binding:** Do not embed variables into log messages. Bind them as contextual kwargs (e.g., `logger.info("fsm_transition", from_state=state_a, to_state=state_b)`).
- **Strict Logging Levels (DEBUG):** Use exclusively for execution tracing. Include raw payloads, matrix dimensions, spatial coordinate bounds, or exact LLM prompt inputs. 
- **Strict Logging Levels (INFO):** Use for systemic lifecycle events only. Examples: service start/stop, completing a major pipeline stage, or FSM node transitions. Do not use for loop iterations.
- **Strict Logging Levels (WARNING):** Use for recoverable anomalies or threshold deviations. Examples: triggering a retry block, falling back to heuristic models when an LLM call fails, or encountering malformed but recoverable spatial geometries.
- **Strict Logging Levels (ERROR/EXCEPTION):** Use only for unrecoverable failures that halt the current unit of work. You must include the full stack trace (`exc_info=True`) and the state of the inputs at the time of failure.


### TypeScript
- Enable and adhere strictly to `tsconfig` `"strict": true`.
- Use `unknown` instead of `any` when a type is not yet known. Force type narrowing before usage.
- Always use `zod` for runtime data validation at system boundaries (e.g., API responses, inputs).
- Use Discriminated Unions to model complex states and Finite State Machines. 
- Always use exhaustive `switch` statements (using a `never` type check in the default case) when evaluating Discriminated Unions to ensure all states are handled.
- Prefer `readonly` properties and `ReadonlyArray` to enforce immutability by default.
- Use `vitest` for testing. 
- Avoid `class`-based inheritance for data models; prefer functional composition and interfaces.

#### Observability & Logging (TypeScript)

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

## Setup commands
* `uv sync`
* `uv run pytest`

## Workspace mapping
* `/src/orchestrator`: Pydantic AI HFSM (Hierarchical Finate State Machine) logic, state definitions, and GraphRunContext.
* `/src/mcp_mesh`: Python-based MCP servers (Xero, Slack, Notion mocks).
