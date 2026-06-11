# ADR-0011: Governed Multi-Agent Collaboration Layer

## Status

Accepted

## Context

Phase 9 transforms the platform from a governed semantic execution platform into a collaborative multi-agent platform. The repository already supports governed agents, orchestration, provenance and execution, but specialist agents need a collaboration model that remains observable, auditable, explainable and governance-bound.

## Decision

Add a domain-neutral Multi-Agent Collaboration Layer with RDF vocabulary, registry data, SHACL validation, SPARQL queries, Python service modules, Flask APIs and dashboards.

The layer represents:

- agent teams, roles and capabilities
- governed delegations from goals to tasks to assigned agents
- shared semantic memory
- conversations, recommendations, negotiations and consensus
- conflicts, resolutions and escalations
- accountability and explainability records

All collaboration records use PROV-O and agent governance metadata. Agents may collaborate and prepare governed execution handoffs, but they may not self-modify, recursively create agents or autonomously change governance assets.

## Consequences

- Multi-agent collaboration is explicit RDF data, not hidden runtime state.
- Flask remains thin; business logic lives under `src/semantic_platform/multi_agent/`.
- CI validation now includes collaboration ontology, SHACL shapes, smoke scripts and tests.
- Phase 10 can build on this layer for broader federation without weakening Phase 9 governance constraints.
