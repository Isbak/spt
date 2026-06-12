"""Map the current Flask view to a governed data scope for the chat panel.

The global chat drawer is context-aware: it tells the read-only assist which graph
scope backs the page the user is looking at, so "what am I looking at?" is answered
against the right data. Scopes mirror the agent context scopes in
``semantic_platform.agents.context`` (ontology / reference / governance / provenance /
reasoning); anything unmapped falls back to ``reference``.

The same logical views are mounted in two trees (System and Knowledge Model); the KM
tree uses ``model_``-prefixed blueprints, which we strip before lookup so both resolve to
the same scope. ``context_aware`` reports whether the current view is dual-mounted (reads
the ``rdf/`` tree) — system-only operational views are flagged ``False`` so the UI can
note they are not domain-scoped.
"""

from __future__ import annotations

DEFAULT_SCOPE = "reference"

#: Blueprint name → (scope, human label). Endpoints are ``"<blueprint>.<view>"``.
_BLUEPRINT_SCOPES: dict[str, tuple[str, str]] = {
    "ontology": ("ontology", "Ontology"),
    "domain_models": ("ontology", "Domain models"),
    "shapes": ("ontology", "Shapes"),
    "graph": ("ontology", "Knowledge graph"),
    "named_graphs": ("ontology", "Named graphs"),
    "ontology_version": ("ontology", "Ontology version"),
    "governance": ("governance", "Governance"),
    "provenance": ("provenance", "Provenance"),
    "reasoning": ("reasoning", "Reasoning"),
    "agents": ("reference", "Agents"),
    "advisory": ("reference", "Advisory"),
}

#: Specific endpoints that need a scope different from their blueprint default.
_ENDPOINT_SCOPES: dict[str, tuple[str, str]] = {
    "visualization.governance_dashboard": ("governance", "Governance dashboard"),
    "visualization.provenance_explorer": ("provenance", "Provenance explorer"),
    "visualization.reasoning_dashboard": ("reasoning", "Reasoning dashboard"),
    "visualization.explanations": ("reasoning", "Explanations"),
    "visualization.analytics": ("reasoning", "Analytics"),
    "visualization.ontology_browser": ("ontology", "Ontology browser"),
    "visualization.graph_explorer": ("ontology", "Graph explorer"),
}

#: Blueprints that are dual-mounted across both context trees (read the ``rdf/`` tree).
#: Operational/agent blueprints (e.g. ``agents``, ``advisory``) are System-only.
_CONTEXTUAL_BLUEPRINTS = frozenset(
    {
        "ontology",
        "domain_models",
        "shapes",
        "graph",
        "named_graphs",
        "ontology_version",
        "governance",
        "provenance",
        "reasoning",
        "query",
        "visualization",
    }
)


def _strip_model_prefix(endpoint: str) -> str:
    """Return the System-equivalent endpoint for a (possibly KM) endpoint name."""
    blueprint, _, view = endpoint.partition(".")
    if blueprint.startswith("model_"):
        return f"{blueprint[len('model_'):]}.{view}"
    return endpoint


def resolve_page_context(endpoint: str | None, active_context: str = "system") -> dict[str, str]:
    """Return ``{scope, label, endpoint, context, context_aware}`` for the endpoint."""
    endpoint = _strip_model_prefix(endpoint or "")
    if endpoint in _ENDPOINT_SCOPES:
        scope, label = _ENDPOINT_SCOPES[endpoint]
    else:
        blueprint = endpoint.split(".")[0]
        scope, label = _BLUEPRINT_SCOPES.get(blueprint, (DEFAULT_SCOPE, "Platform"))
    blueprint = endpoint.split(".")[0]
    return {
        "scope": scope,
        "label": label,
        "endpoint": endpoint,
        "context": active_context,
        "context_aware": blueprint in _CONTEXTUAL_BLUEPRINTS,
    }
