# ADR-0008: Agent Integration

## Status
Accepted

## Context
AI agents need trusted, contextual and governed knowledge.

## Decision
Agents consume semantic knowledge through SPARQL and APIs. Agents should not directly modify governed ontology graphs.

## Consequences
Agents are decoupled from storage and can operate on trusted semantic contracts.
