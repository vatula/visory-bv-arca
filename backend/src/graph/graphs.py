from __future__ import annotations

from pydantic_graph import Graph

from src.graph.anomaly import EvaluateVaguenessNode, ExtractLedgerVarianceNode
from src.graph.gathering import (
    CheckDriveNode,
    DispatchSlackNode,
    NormalizeToDriveNode,
    SuspendForSlackNode,
)
from src.graph.policy import EscalateNode, ExtractRulesNode, QueryNotionNode
from src.graph.synthesis import (
    DraftGenerationNode,
    EscalateToHumanReviewNode,
    EvaluateConfidenceNode,
    MarkCompleteNode,
    MergeContextNode,
)
from src.graph.state import ArcraState
from src.services.bedrock import ArcraDeps

anomaly_graph: Graph[ArcraState, ArcraDeps, None] = Graph(
    nodes=[ExtractLedgerVarianceNode, EvaluateVaguenessNode],
    name="AnomalyGraph",
)

policy_graph: Graph[ArcraState, ArcraDeps, None] = Graph(
    nodes=[QueryNotionNode, ExtractRulesNode, EscalateNode],
    name="PolicyGraph",
)

# Full gathering graph: Drive check → optional Slack suspend path
gathering_graph: Graph[ArcraState, ArcraDeps, None] = Graph(
    nodes=[CheckDriveNode, DispatchSlackNode, SuspendForSlackNode, NormalizeToDriveNode],
    name="GatheringGraph",
)

# Resumption graph: single entry point used by /webhook/slack after state reload
resumption_graph: Graph[ArcraState, ArcraDeps, None] = Graph(
    nodes=[NormalizeToDriveNode],
    name="ResumptionGraph",
)

# Synthesis graph: merge context → confidence evaluation → draft or escalate
synthesis_graph: Graph[ArcraState, ArcraDeps, None] = Graph(
    nodes=[
        MergeContextNode,
        EvaluateConfidenceNode,
        DraftGenerationNode,
        EscalateToHumanReviewNode,
        MarkCompleteNode,
    ],
    name="SynthesisGraph",
)
