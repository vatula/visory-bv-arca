from __future__ import annotations

from pydantic_graph import Graph

from src.graph.anomaly import EvaluateVaguenessNode, ExtractLedgerVarianceNode
from src.graph.policy import EscalateNode, ExtractRulesNode, QueryNotionNode
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
