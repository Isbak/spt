# ADR-0013: Governed Read-Only LLM Assist for Agents

## Status
Accepted

## Context
The agent layer (ADR-0008) was deliberately representational, with no LLM integration and
no autonomous behaviour. Users wanted agents to actually generate natural-language
explanations and summaries — but without giving up the platform's governance guarantees
(permissions, provenance, non-autonomy), and without forcing an external dependency or API
key on a platform that is otherwise self-contained.

## Decision
Add a **governed, opt-in, read-only LLM assist**:

- `agents/assist.py` exposes `generate_explanation(agent_id, scope, question)`. It resolves the
  agent, **enforces the agent's read permission** for the scope (the same safety check the
  context provider uses — denial raises `PermissionError`), retrieves only the in-scope facts,
  asks the model to explain them, and records a **PROV-O** activity attributed to the agent and
  the model used.
- The model only turns a prompt into text. It **never** selects tools, drives plans, or writes
  to the knowledge graph, so the non-autonomy guarantee (and its enforcing test) is preserved.
- `agents/llm.py` makes the model **pluggable**, in two tiers:
  - **Self-contained** (no API key, no third-party cloud): `local` — a free, offline,
    deterministic model (the default, runs in CI); and `ollama` — a **real** local LLM served by
    a bundled Ollama container (`docker compose --profile llm up` / `make docker-up-llm`), the LLM
    counterpart to the bundled Fuseki triple store.
  - **External**: Anthropic (official SDK, `claude-opus-4-8`) and OpenAI — third-party cloud APIs
    requiring credentials.
  - All are selected via `LLM_PROVIDER`/`LLM_MODEL` and import their SDK lazily.
- Surfaced through `api.explain_with_agent` and a `GET /api/agents/<id>/explain` route that
  returns 403 on permission denial.

## Consequences
Agents can produce explanations while every governance property holds: permission-checked,
read-only, provenance-recorded, non-autonomous. The platform stays self-contained by default
(the free local model runs in CI with no credentials); real LLMs are a configuration change,
mirroring the optional external mode of the materialization layer (ADR-0012). This relaxes the
original "no LLM integrations" stance from ADR-0008 to a **governed exception**, documented here
and in CLAUDE.md.
