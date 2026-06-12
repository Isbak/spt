# ADR-0016: Governed Conversational Authoring (Modelling Studio)

## Status
Accepted

## Context
The LLM assist (ADR-0013) is deliberately **read-only**: it explains data an agent may
already read and never writes anything. Users asked for the next step — to *chat with a
setup bot* to configure models and to *talk with their data* — and, beyond that, to have the
assistant help **author the knowledge architecture itself**: scaffold ontologies, SHACL
shapes, mappings and sample data for a specific domain through a guided conversation, with the
files written somewhere they can review and accept them.

This crosses the read-only boundary of ADR-0013, so it needs an explicit decision about how
writing can happen without giving up the platform's governance and non-autonomy guarantees.

## Decision
Add a **governed conversational authoring** capability (`semantic_platform/authoring/`) plus a
**global, context-aware chat panel** and **setup pages**, surfaced through `api.py` and three
Flask blueprints (`chat`, `setup`, `studio`).

Writing is allowed, but fenced by these guarantees:

- **Never the platform's own graph.** Generated files are written **only** into a sandboxed
  clone of a **separate, user-configured domain content repository** (`workspace_config.py`
  maps a *domain of interest* → git remote/branch/token), on a feature branch under
  `WORKSPACE_ROOT`. The platform's authoritative `rdf/` tree is never modified.
- **Human review via Pull Request.** Generated files are committed to a sandbox branch and
  surfaced as a git diff / PR (`gitrepo.py`); a **human reviews and merges**. There is no
  autonomous merge and no execution against the platform graph.
- **Validated.** Scaffolded Turtle is valid and SHACL-conformant by construction
  (`scaffold.py`) and re-checked with the existing `validate_rdf_syntax` gate before commit.
- **PROV-recorded.** Each authoring turn records a PROV-O activity (mirroring the assist).
- **Provider-governed.** The model is resolved via the same pluggable layer (ADR-0013). A new
  `auto` provider makes **Anthropic and Ollama first-class** (Anthropic if a key is set, else a
  reachable local Ollama, else the offline `local` model). The headless/CI default stays
  `local`, preserving the offline guarantee.

The chat panel has two modes: **ask** (read-only Q&A scoped to the data behind the current
page, routed through `explain_with_agent` — 403 on permission denial) and **model** (the
authoring conversation for a selected domain; if none is configured it points the user at
Settings → Domain Repos first).

## Testing
Deterministic and offline: scaffolding and the `local` model run in CI; git operations are
exercised via `file://` remotes (no network); push and PR-creation degrade to a compare link
and are marked `pragma: no cover`. Route tests assert the 403 (denied scope), the
`needs_domain_setup` prompt, and the write→validate→read round-trip.

## Consequences
The platform gains a guided way to build domain knowledge models, while every governance
property is preserved by relocating the write target (a separate, human-reviewed repo) rather
than relaxing control over the platform graph. This extends ADR-0013's "governed exception"
from read-only explanation to **review-gated authoring**, and complements the approval-gated
`GovernedExecutor` (ADR-0008/execution) philosophy: machines draft, humans approve.
