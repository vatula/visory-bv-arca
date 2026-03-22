# Telemetry & API Architecture

## The Dual-Stream Observability Pipeline

The backend relies on a centralized `structlog` configuration to act as the event multiplexer. 
The Pydantic Graph nodes do not interact with the database directly for audit trails; 
they emit structured events.

### 1. The Graph Execution (Producer)

Nodes use a standard logger instance. When an event should be visible in the Next.js Frontend Console, it is flagged via `is_telemetry=True`.

```python
logger.info(
    "policy_extracted",
    is_telemetry=True,
    transaction_id=state.session_id,
    node="PolicyGraph",
    action_summary="Extracted policy bounds",
    confidence_score=0.92
)
```

### 2. The Multiplexer (`structlog` Processors)

The `structlog` pipeline is configured with a fork.

 - **Stream 1 (Standard Observability):** The event dict passes through standard processors (timestamping, log level addition) and is formatted by `structlog.dev.ConsoleRenderer` (for local dev) or `structlog.processors.JSONRenderer` (for production log aggregation like Datadog/CloudWatch) directly to `stdout`.
 - **Stream 2 (The Read Model Sink):** A custom processor (`sqlite_read_model_sink`) intercepts the dictionary before it is serialized to a string. If `is_telemetry=True` is present, it asynchronously writes the event into the SQLite Read Model.

## CQRS Database Schema (SQLite)

The backend maintains specific tables dedicated entirely to serving the Next.js frontend, hydrated exclusively by the Stream 2 sink.

```sql
-- Read-Optimized table for the Dashboard (Active/Processed Queues)
CREATE TABLE arcra_ui_read_model (
    transaction_id TEXT PRIMARY KEY,
    status TEXT, -- 'pending', 'processing', 'suspended', 'resolved', 'escalated'
    amount DECIMAL,
    merchant TEXT,
    employee_name TEXT,
    confidence_score REAL,
    synthesis_reasoning TEXT,
    last_updated TIMESTAMP
);

-- Audit Trail table (Chronological Node Traversals)
CREATE TABLE arcra_audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT,
    timestamp TIMESTAMP,
    node_name TEXT,
    action_summary TEXT,
    slack_channel TEXT, -- Populated if action involves Slack MCP
    slack_message_sent TEXT, 
    slack_reply_received TEXT 
);
```

### OpenAPI 3.0 Integration (FastAPI)

FastAPI acts as the boundary layer between the SQLite Read Model and the Next.js frontend. It exposes mathematically rigorous Pydantic models as an OpenAPI 3.0 specification.

**Key Endpoints:**
 - `GET /api/v1/transactions/active` Scans `arcra_ui_read_model` for non-terminal states. Used to populate the left column of the Frontend Console.
 - `GET /api/v1/transactions/processed` Scans `arcra_ui_read_model` for terminal states. Used to populate the right column of the Frontend Console.
 - `GET /api/v1/transactions/{id}/audit` Performs a composite query, returning the root transaction details and a chronological array of `arcra_audit_events`. This payload directly hydrates the Frontend's `AuditTimeline` and `SlackInteractionViewer` components.