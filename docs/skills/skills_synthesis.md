# Required Skills Profile: Synthesis & Xero Draft (Phase 4)

## Core Competencies Required

### Advanced Prompt Engineering & Structured Extraction (AWS Bedrock)
 - **Skill:** Designing deterministic, instruction-bound prompts for anthropic.claude-3-sonnet-20240229-v1:0 via the Bedrock Converse API.  
 - **Application:** Forcing the LLM to process a highly complex, merged context window (transaction\_data \+ policy\_context \+ evidence\_documents) and output a strict, mathematically rigid JSON schema containing a confidence\_score (float) and reasoning (string).  
 - **MLOps Focus:** Handling non-deterministic edge cases gracefully (e.g., what happens if the model refuses to score or outputs a malformed schema).

### Pydantic Graph Orchestration
 - **Skill:** Implementing terminal graph nodes (BaseNode) and deterministic conditional edge routing.  
 - **Application:** Building the MergeContextNode and EvaluationNode. Implementing the strict threshold logic that routes the graph either to DraftGenerationNode (if confidence\_score \>= settings.CONFIDENCE\_THRESHOLD) or EscalateToHumanReviewNode.  
 - **Constraint:** Maintaining pure functions within the nodes. State mutations must be explicitly returned via the graph's State object, not modified in place.

### API Payload Synthesis & Tool Calling (Xero via MCP)
 - **Skill:** Strict data transformation and schema compliance for external accounting APIs.  
 - **Application:** Mapping the synthesized, validated graph state into a valid Xero draft invoice payload. This includes correctly attaching the gathered Drive URIs as supporting evidence to the drafted ledger entry.

### CQRS Telemetry & Observability (structlog)
 - **Skill:** Dual-stream event logging and data facade management.  
 - **Application:** Emitting the final confidence\_score, reasoning trace, and terminal status as structured telemetry (logger.info(..., is\_telemetry=True)). This ensures the UI Read Model (arcra\_ui\_read\_model) is accurately hydrated for the human auditor without coupling the graph node to the SQLite database.