"""Map the current Flask view to a governed data scope for the chat panel.

The global chat drawer is context-aware: it tells the read-only assist which graph
scope backs the page the user is looking at, so "what am I looking at?" is answered
against the right data. Scopes mirror the agent context scopes in
``semantic_platform.agents.context`` (ontology / reference / governance / provenance /
reasoning); anything unmapped falls back to ``reference``.
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


def resolve_page_context(endpoint: str | None) -> dict[str, str]:
    """Return ``{scope, label, endpoint}`` for the current request endpoint."""
    endpoint = endpoint or ""
    if endpoint in _ENDPOINT_SCOPES:
        scope, label = _ENDPOINT_SCOPES[endpoint]
    else:
        blueprint = endpoint.split(".")[0]
        scope, label = _BLUEPRINT_SCOPES.get(blueprint, (DEFAULT_SCOPE, "Platform"))
    return {"scope": scope, "label": label, "endpoint": endpoint}
