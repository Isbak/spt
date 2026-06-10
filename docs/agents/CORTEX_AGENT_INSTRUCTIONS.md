
# Cortex Agent Instructions

You are working in a semantic platform repository.

Before making changes, read:

1. README.md
2. ARCHITECTURE.md
3. docs/adr/ADR-INDEX.md
4. docs/c4/C4_MODEL.md
5. docs/governance/GOVERNANCE_MODEL.md
6. docs/ontology/ONTOLOGY_DEVELOPMENT_GUIDE.md
7. docs/agents/AGENT_ARCHITECTURE_GUIDE.md

## Core Rules

- Keep the platform domain-neutral.
- Do not introduce domain-specific examples unless explicitly requested.
- Treat RDF, OWL, SHACL, SPARQL, PROV-O and R2RML as first-class capabilities.
- Preserve named graph strategy.
- Preserve provenance for generated data.
- Keep Flask thin.
- Keep business logic in src/semantic_platform.
- Keep Fuseki integration configurable.
- Do not hardcode credentials.
- Add tests for all changed behavior.
- Ensure make verify passes.

## Architecture Rules

- Architectural changes require ADR updates.
- Structural changes require C4 updates.
- Ontology changes require version updates.
- Governance changes require ownership metadata.
- Agent integration must use API/SPARQL boundaries.

## Output Expectations

For every task:

1. Explain what changed.
2. List files changed.
3. State tests executed.
4. State whether make verify passed.
