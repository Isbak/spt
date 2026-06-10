# C4 Component

See `C4_MODEL.md`.

## Phase 6 Agent Integration Components

The Semantic Platform application now includes an Agent Integration Layer composed of:

- Agent Registry for managed agent metadata and lifecycle status.
- Agent Governance and Safety for ownership, approval, permissions, graph access, and tool access validation.
- Agent Context Provider for governed ontology, reference, governance, provenance, and reasoning context retrieval.
- Agent Memory Store for working, session, semantic, and observation memory RDF resources.
- Agent Tool Registry for governed graph query, semantic search, provenance, governance, and analytics tools.
- Agent Provenance Recorder for Agent -> Execution -> Observation -> Decision -> Output chains.
- Agent Observation Log for requests, actions, failures, warnings, graph access, and tool usage metrics.
- Agent Planner for Goal -> Tasks -> Actions planning without autonomous execution.

The Flask layer remains thin and exposes `/api/agents` API endpoints plus `/agents` UI routes that call the service layer in `src/semantic_platform/agents/`.
