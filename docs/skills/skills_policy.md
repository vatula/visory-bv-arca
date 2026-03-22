# Required Skills Profile: Policy Extraction (Phase 2)

## Core Competencies Required

### Semantic Context Translation
 - **Skill:** Prompt engineering for unstructured-to-structured data transformation.  
 - **Application:** Reading raw markdown files from `resources/policies/*.md` (simulating the Notion MCP server payload) and forcing the LLM to extract actionable mathematical or boolean rules (e.g., spending limits, required project codes) relevant to the active transaction.

### Stateful Context Appending (`pydantic_graph`)
 - **Skill:** Managing accumulating graph state without overwriting context.  
 - **Application:** Injecting the extracted rules into the `policy_context` key of the `ArcraState` object. Ensuring this transition triggers the required telemetry hook (`is_telemetry=True`) so the UI Read Model accurately reflects the policy extraction step in the audit timeline.

### Edge Case Routing & Escapement
 - **Skill:** Designing deterministic fallback routes in the graph.  
 - **Application:** Handling failures gracefully—such as missing local policy documents or API timeouts—by routing the graph edge explicitly to a Human Escalate node rather than allowing the graph to crash.