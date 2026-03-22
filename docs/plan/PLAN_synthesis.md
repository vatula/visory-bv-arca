# Synthesis & Evaluation FSM Plan

## Core Responsibility
The final autonomous reasoning step. Consolidates the initial transaction, the extracted policy rules, and the gathered evidence (from Drive or Slack). Uses Pydantic AI's `BedrockModel` to calculate a confidence score and push the final draft to Xero via MCP.

## FSM Visualization

```plantuml
@startuml
!theme amiga
state "SynthesisGraph" as Synthesis {
    [*] --> MergeContextNode
    
    MergeContextNode --> EvaluationNode
    
    state EvalChoice <<choice>>
    EvaluationNode --> EvalChoice
    
    EvalChoice --> DraftGenerationNode : [confidence >= threshold]
    EvalChoice --> EscalateToHumanReviewNode : [confidence < threshold]
    
    DraftGenerationNode --> PushToXeroNode
    PushToXeroNode --> [*] : [Resolved: Xero Draft Created]
    
    EscalateToHumanReviewNode --> [*] : [Low Confidence: Escalate]
}
@enduml
```