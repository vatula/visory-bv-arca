# Tasks: Anomaly Detection FSM

- [ ] **Data Layer:** Refactor `src/infrastructure/db.py` to initialize the `arcra_checkpoints` and `arcra_interrupts` SQLite tables. Remove all Celery and Redis configurations.
- [ ] **State Definition:** Define the unified `ArcraState` model (e.g., using `TypedDict` or `BaseModel`) that will flow through the entire graph. It must contain `transaction_data`, `policy_context`, `evidence_documents`, and `validation_confidence`.
- [ ] **Service Layer:** Implement `BedrockService` using the Converse API. Enforce strict JSON output schemas for anomaly routing.
- [ ] **Node Implementation (`ExtractLedgerVarianceNode`):** Initialize the graph execution thread. Parse the Xero context to prepare for Bedrock evaluation.
- [ ] **Node Implementation (`EvaluateVaguenessNode`):** Pass transaction details to Bedrock. 
- [ ] **Edge Routing:** Instead of dispatching to a queue, return a state update. If `anomaly_detected` is true, route the graph edge to `PolicyGraph`. If false, route to the `END` node.