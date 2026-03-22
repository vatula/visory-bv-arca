# Tasks: Policy Verification FSM
- [x] **Node Implementation (`QueryNotionNode`):** The graph transitions here natively, carrying the full `ArcraState` in memory. Execute the semantic search against the Notion MCP server (simulated via deterministic keyword routing to `resources/policies/*.md` — PLAN_OVERRIDE #5).
- [x] **Node Implementation (`ExtractRulesNode`):** Pass the raw policy markdown to a Pydantic AI `Agent` using `BedrockConverseModel`. Extract constraints (e.g., "requires receipt") into a structured `PolicyRuleContainer` using Pydantic `output_type`.
- [x] **State Update:** Append the extracted rules to the `policy_context` key within the graph's state object.
- [x] **Edge Routing:**
    - *Success:* Route edge to `End` (state status=`policy_extracted`). Ready for Phase 3 `GatheringGraph` handoff.
    - *Failure (Missing/Error):* Route edge to `EscalateNode` (Human Review Queue).
