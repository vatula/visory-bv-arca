# ARCRA Architectural Constitution

## 1. Configuration & Dependency Injection
* Use `pydantic-settings` `BaseSettings` class to load and validate the application configuration. **DO NOT** use raw environment calls.
* Pass the validated configuration object into FSM nodes strictly via the `GraphRunContext` `deps` attribute.

## 2. Strict HFSM Routing & State Partitioning
* Every FSM node MUST subclass `pydantic_graph.BaseNode`.
* The `run` method MUST explicitly annotate its return type to represent ONLY permitted subsequent nodes.
* **CRITICAL:** Root Graph nodes must act purely as delegates. They must instantiate a Sub-Graph, run it, and map the returned Sub-Graph state back to the central `ArcraState`. 

## 3. Epistemic Confidence & Escalation
* `SynthesisGraph` must perform a programmatic self-evaluation. 
* If the probability of correctness falls below the configured `CONFIDENCE_THRESHOLD`, the FSM must immediately transition to the `HumanInterventionNode` in the Root Graph, packaging the `audit_trail` for the human user.

## 4. Data Validation & Rate Limit Safety
* Enforce `strict=True` globally on all Pydantic models handling external data payloads.
* All external MCP tool calls must utilize exponential backoff and enforce `max_steps` to prevent infinite loops.
* Utilize `BaseStatePersistence` in `GatheringGraph` when transitioning to states requiring asynchronous human input.