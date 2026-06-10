# Agent Architecture Guide

## Principle

Agents consume semantic knowledge. They should not own the source of truth.

## Access Pattern

```text
Agent
  |
  v
API / SPARQL
  |
  v
Semantic Platform
```

## Read Graphs

- ontology
- reference
- provenance
- governance

## Write Graphs

- sandbox
- integration

## Agent Rules

- Do not directly modify governed ontology graphs.
- Use provenance for every generated assertion.
- Prefer explainable SPARQL queries over hidden assumptions.
- Treat graph outputs as contextual evidence, not absolute truth.

## Phase 6 Agent Integration Layer

Phase 6 adds a domain-neutral Agent Integration Layer under `src/semantic_platform/agents/`.
Agents are first-class governed semantic entities represented in RDF and exposed through
Flask APIs and UI routes. The layer supports registry lookup, governance validation,
permission checks, context retrieval, memory, tool access, provenance chains,
observability metrics, and planning.

The runtime is intentionally non-autonomous. Agents can retrieve governed context, use
registered tools, create explainable outputs, and record provenance, but they must not
execute business workflows, delegate to other agents, self-modify, or write directly to
ontology, governance, or provenance graphs during normal operation.

### Governed interaction flow

```text
User
  -> AgentRuntime
  -> Safety and permissions
  -> Governed semantic context / tools
  -> Knowledge graph and reasoning context
  -> Provenance, observations, memory
  -> Explainable output
```

### Phase 6 constraints

- Agents must be registered in `rdf/data/agent_registry.ttl`.
- Agents must have owner, steward, version, approval status, graph access, and tool access.
- Agent writes are limited to sandbox and integration scopes by default.
- Ontology, governance, and provenance writes require explicit approval and are not part of normal runtime behavior.
- Planning creates reviewable plans only; it does not execute actions.
