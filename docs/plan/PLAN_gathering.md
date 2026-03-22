# Evidence Gathering FSM Plan

## Core Responsibility
Autonomously traverse Drive via MCP. If context is still missing, ping Slack and natively interrupt graph execution. Compute is released until an external webhook resumes the state.

## FSM Visualization

```plantuml
@startuml
!theme amiga
state "GatheringGraph" as Gathering {
    [*] --> CheckDriveNode
    
    state DriveChoice <<choice>>
    CheckDriveNode --> DriveChoice
    DriveChoice --> [*] : [Found in Drive: Route to SynthesisGraph]
    DriveChoice --> CheckSlackNode : [Missing]
    
    CheckSlackNode --> WaitForHumanInterruptNode : [Message Sent via Slack MCP]
    
    state "Graph Suspended (Compute Released)" as Suspended
    WaitForHumanInterruptNode --> Suspended : [Yield Execution]
    
    state ResumeChoice <<choice>>
    Suspended --> ResumeChoice : [External Webhook Trigger / Timeout]
    
    ResumeChoice --> NormalizeToDriveNode : [Payload Received]
    ResumeChoice --> TimeoutNode : [48 Hours Reached]
    
    NormalizeToDriveNode --> [*] : [Context Appended: Route to SynthesisGraph]
    TimeoutNode --> [*] : [Move to Human Review Queue]
}
@enduml