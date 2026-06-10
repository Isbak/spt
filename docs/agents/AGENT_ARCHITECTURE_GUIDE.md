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
