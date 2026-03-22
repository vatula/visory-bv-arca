# Tasks: Policy Verification FSM

- [ ] **Node Implementation (`QueryNotionNode`):** The graph transitions here natively, carrying the full `ArcraState` in memory. Execute the semantic search against the Notion MCP server.
- [ ] **Node Implementation (`ExtractRulesNode`):** Pass the raw Notion markdown to a Pydantic AI `Agent` using `BedrockModel`. Extract constraints (e.g., "requires receipt") into a structured JSON array using Pydantic `result_type`.
- [ ] **State Update:** Append the extracted rules to the `policy_context` key within the graph's state object. 
- [ ] **Edge Routing:** - *Success:* Route edge to `GatheringGraph`. The checkpointer will automatically persist this state transition to SQLite.
    - *Failure (Missing/Error):* Route edge to `EscalateNode` (Human Review Queue).