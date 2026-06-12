# ADR-0018: System vs Knowledge Model Data-Context Trees

## Status
Accepted

## Context
Every UI view historically read the platform's **own** authoritative `rdf/` tree via
`Settings` — the platform self-model. Separately, the Modelling Studio (ADR-0016) lets a
user author a *domain* knowledge model in a **separate, user-configured git repository**
cloned under the workspace. There was no way to inspect a domain's model through the
platform's rich views (ontology, graph, shapes, reasoning, governance, provenance, …): the
only domain-facing surface was the Studio file editor.

Users want to **separate the UI by data context** and to *visualize a knowledge model from
every angle*, not just edit its files. The two contexts are expected to **diverge** over
time (the Knowledge Model context will grow its own authoring affordances the System
context does not have), so the separation must be a real architectural boundary rather than
a flag threaded through shared routes.

## Decision
Serve the same views through **two separate blueprint trees**, distinguished only by which
`Settings` they read:

- **System** context (default): the platform self-model, at today's URLs — unchanged. The
  existing `app/routes/*` blueprints are the System tree.
- **Knowledge Model** context: a **selected configured domain**, mounted under
  `/model/<domain_id>/…` (`app/contexts/knowledge_model/`). The Studio remains the
  *modelling/edit* surface for a domain; these angle-views are the *visualize from every
  angle* surface. Together they form the Knowledge Model context, cross-linked both ways.

Mechanics:

- **One lever — a domain-scoped `Settings`.** `semantic_platform/context.py:domain_settings`
  returns a `Settings` whose `rdf_*` path fields point at the domain repo's `rdf/` subtree
  (which mirrors the system layout), cloning/initialising the repo on first use. Non-RDF
  fields (Fuseki, workspace, LLM) are untouched. The package is domain-neutral and never
  imports from `app`.
- **One boundary object — `ContextScope`** (`app/context_scope.py`) bundles the active
  context's id, label, resolved `Settings`, and a tree-aware `url_for`. It is bound to
  `g.scope` once per request from the `domain_id` in the URL (System when absent; 404 for an
  unknown domain). Only `scope.settings` ever flows into the package.
- **Shared view logic, not duplicated.** Each applicable view's body lives in a
  context-agnostic `app/views/*.py:render(scope)` function that both trees bind to their
  endpoints. Divergence later means a tree stops sharing one render function — no context
  flags in shared code.
- **Scope of views.** Views that read the `rdf/` tree are dual-mounted (ontology, graph,
  domain models, shapes, named graphs, ontology version, governance, provenance, reasoning,
  inferences, consistency, explanations, analytics, query, search). Reasoning **rules**
  remain System-wide (governed platform rules are cross-domain). Operational/agent/business
  views (health, setup, studio, agents, advisory, orchestration, execution, multi-agent,
  fabric, mappings, materialization, source catalog) stay **System-only**.
- **UI.** A topbar context switcher (System + each configured domain) appears on
  dual-mounted views and swaps trees for the current view; contextual nav links follow the
  active tree via `scope.url_for`; a Knowledge Model context bar links back to the Studio.

A missing explicit RDF file (e.g. a domain with no `graphs/manifest.ttl`) is now skipped by
`graph.load_graph` rather than raising, so an unscaffolded domain renders empty instead of
erroring — consistent with how missing directories already yield nothing.

## Consequences
- The platform's view set works over any configured domain with no per-view rewrite — the
  same governance and non-autonomy guarantees hold, since the package layer is unchanged
  except the new context factory.
- System URLs, endpoint names, and behavior are preserved (regression-guarded), so existing
  bookmarks, tests, and `url_for` calls keep working.
- The two contexts can diverge independently: a future Knowledge-Model-only feature is added
  solely to the KM tree without touching System.
- The boundary is purely UI/app-layer; no new Make/`ci-validate` targets are required.
