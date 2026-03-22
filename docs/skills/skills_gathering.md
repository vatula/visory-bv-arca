# Required Skills Profile: Stateful Interruption & Gathering (Phase 3)

## Core Competencies Required

### Native Graph Checkpointing & Suspension
 - **Skill:** Utilizing Pydantic Graph's native interrupt mechanisms (`NodeInterrupt` or equivalent yield states).  
 - **Application:** **High Complexity.** Halting the execution thread entirely when human context is required (simulating a Slack ping). The agent must understand that compute is released and the graph is serialized to SQLite (`arcra_checkpoints`) awaiting an external trigger.

### Asynchronous Webhook Integration (FastAPI)
 - **Skill:** Building state-resumption endpoints.  
 - **Application:** Implementing the `/webhook/slack` FastAPI route that catches external payloads, looks up the suspended graph via its `thread_id`, and natively resumes the graph state, injecting the human response.

### Multimodal Resource Simulation
 - **Skill:** Local filesystem interaction simulating MCP document retrieval.  
 - **Application:** Building the logic to traverse `resources/invoices/*.pdf` to simulate a Google Drive search. If the file exists, append the URI to the `evidence_documents` state. If missing, trigger the Slack interrupt.