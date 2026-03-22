# Required Skills Profile: Foundation & Observability Pipeline (Phase 1)

## Core Competencies Required

### Advanced Structured Logging & Interception (`structlog`)
 - **Skill:** Building custom structlog processors and dual-stream multiplexers.
 - **Application:** Decoupling the execution graph from the database. The agent must implement an interceptor that catches `logger.info(..., is_telemetry=True)`, parses the payload, writes it asynchronously to the SQLite Read Model, and strips the telemetry flag before passing it to `stdout`.

### CQRS Data Modeling (SQLite)
 - **Skill:** Designing decoupled database schemas optimized for specific access patterns.
 - **Application:** Initializing the distinct table structures for both the native graph checkpointer (`arcra_checkpoints`) and the UI Read Models (`arcra_ui_read_model`, `arcra_audit_events`). Ensuring thread-safe, strict relational bounds even within a lightweight engine like SQLite.

### API Boundary Design (FastAPI)
 - **Skill:** Designing mathematically rigorous REST APIs utilizing Pydantic V2.
 - **Application:** Exposing the SQLite Read Models as an OpenAPI 3.0 specification. This boundary must strictly define the payload schemas for transaction states, confidence scores, and chronological audit trails to ensure the Next.js frontend has a strongly typed contract.