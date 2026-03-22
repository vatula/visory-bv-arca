# Required Skills Profile: Ingestion & Anomaly Detection (Phase 2)

## Core Competencies Required

### Deterministic State Machine Orchestration (`pydantic_graph`)
 - **Skill:** Defining Graph States and foundational node execution using `pydantic_graph`.  
 - **Application:** Initializing the `ArcraState` model with strict Pydantic V2 validations. Building the entry point nodes that ingest the `xero_api_feed.json` fixture and manage the initial state transitions based on structural ledger variance.

### Guardrailed LLM Execution (AWS Bedrock)
 - **Skill:** Utilizing `boto3` and the Bedrock Converse API to perform semantic variance checks.  
 - **Application:** Prompting the LLM to identify vagueness or missing context in a transaction ledger line. The execution must strictly enforce a JSON output schema indicating whether the anomaly requires routing to the deeper policy/evidence graphs.

### Pure Function Design & Dependency Injection
 - **Skill:** Isolating side effects in execution nodes.  
 - **Application:** Injecting the `BedrockService` via the `GraphRunContext` rather than instantiating it globally or within `__init__`. Ensuring state mutations are exclusively handled by returning updated graph states.