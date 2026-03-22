# Required Skills Profile: Agentic Observability Console (Phase 5)

## Core Competencies Required

### Type-Safe Client Engineering (TypeScript)
* **Skill:** Code generation from OpenAPI specifications and strict TypeScript implementation.  
* **Application:** Generating the client-side API layer directly from the FastAPI `openapi.json` contract. Ensuring `strict: true` is enabled in `tsconfig.json` and `unknown` types are validated via Zod where runtime boundary checks are needed.

### MLOps Observability UI/UX Design
* **Skill:** Designing dense, data-rich interfaces using Next.js (App Router) and Tailwind CSS.  
* **Application:** Building the specialized UI components (`AuditTimeline`, `SlackInteractionViewer`, `SynthesisMetrics`). Translating the agent's non-deterministic reasoning trace and float-based confidence scores into an easily auditable format for a human bookkeeper.

### Client-Side Telemetry (`pino`)
* **Skill:** Implementing structured logging in the browser environment.  
* **Application:** Configuring `pino` to log UI state changes and API fetch events, completely avoiding the native `console` API. Ensuring fatal React boundary errors are caught and logged structurally.