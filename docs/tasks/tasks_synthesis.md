# Tasks: Synthesis & Evaluation FSM (Revised)

- [ ] **Node Implementation (`EvaluationNode`):** The node receives the fully populated `ArcraState` natively. Pass the transaction, policy context, and evidence URIs to `BedrockService`. Require a JSON output containing `confidence_score` and `reasoning`.
- [ ] **Threshold Logic & Routing:** Compare `confidence_score` against `settings.CONFIDENCE_THRESHOLD`.
    - *If >= Threshold:* Route to `DraftGenerationNode`.
    - *If < Threshold:* Route to `EscalateToHumanReviewNode`.
- [ ] **Node Implementation (`DraftGenerationNode`):** Invoke the Xero MCP to create the draft transaction. Attach the Drive URIs.
- [ ] **Node Implementation (`EscalateToHumanReviewNode`):** Flag the transaction in the external UI database for human review, appending the state history.
- [ ] **Node Implementation (`MarkCompleteNode`):** Reaches the `END` node of the graph. Execution terminates cleanly.
