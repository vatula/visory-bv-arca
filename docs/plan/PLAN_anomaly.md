# Anomaly Detection FSM Plan

## Core Responsibility
Ingest the transaction, perform the initial variance check via AWS Bedrock, and determine if the macro graph should proceed to deeper policy verification or terminate early.

## FSM Visualization

```plantuml
@startuml
!theme amiga
state "AnomalyGraph" as Anomaly {
    [*] --> ExtractLedgerVarianceNode
    
    state ExtractChoice <<choice>>
    ExtractLedgerVarianceNode --> ExtractChoice
    ExtractChoice --> EvaluateVaguenessNode : [Data Valid]
    ExtractChoice --> [*] : [Xero API Error]
    
    state VaguenessChoice <<choice>>
    EvaluateVaguenessNode --> VaguenessChoice
    
    VaguenessChoice --> [*] : [Anomaly Detected: Route to PolicyGraph]
    VaguenessChoice --> [*] : [Normal: End Execution]
}
@enduml
```