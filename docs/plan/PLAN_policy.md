# Policy Verification FSM Plan

## Core Responsibility
Interfaces with the Notion MCP server to retrieve corporate rules and extracts semantic constraints via Pydantic AI's `BedrockModel` to inform the evidence gathering phase.

## FSM Visualization

```plantuml
@startuml
!theme amiga
state "PolicyGraph" as Policy {
    [*] --> QueryNotionNode
    
    state QueryChoice <<choice>>
    QueryNotionNode --> QueryChoice
    QueryChoice --> ExtractRulesNode : [Policy Found]
    QueryChoice --> ErrorNode : [Notion API Error / Missing]
    
    ExtractRulesNode --> [*] : [Rules Appended to State: Route to GatheringGraph]
    ErrorNode --> [*] : [Escalate to Human Review]
}
@enduml
```