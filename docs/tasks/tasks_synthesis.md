# Tasks: Synthesis & Evaluation FSM
- [x] **Node Implementation (`EvaluationNode`):** The node receives the fully populated `ArcraState` natively. Pass the transaction, policy context, and evidence URIs to a Pydantic AI `Agent` (powered by `BedrockModel`). Require a JSON output (via `result_type`) containing `confidence_score` and `reasoning`.
- [x] **Threshold Logic & Routing:** Compare `confidence_score` against `settings.CONFIDENCE_THRESHOLD`.
    - *If >= Threshold:* Route to `DraftGenerationNode`.
    - *If < Threshold:* Route to `EscalateToHumanReviewNode`.
- [x] **Node Implementation (`DraftGenerationNode`):** Invoke the Xero MCP to create the draft transaction. Attach the Drive URIs.
- [x] **Node Implementation (`EscalateToHumanReviewNode`):** Flag the transaction in the external UI database for human review, appending the state history.
- [x] **Node Implementation (`MarkCompleteNode`):** Reaches the `END` node of the graph. Execution terminates cleanly.
