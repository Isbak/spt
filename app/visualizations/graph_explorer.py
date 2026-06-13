"""Graph explorer visualization data service (System reference graph).

The pure node/edge and node-detail builders live in
:mod:`semantic_platform.graph_view` so they can be reused for domain workspaces
without the package importing from the Flask layer. This module wires them to the
configured System graph and re-exports them for the app layer and tests.
"""

from __future__ import annotations

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.graph_view import build_graph_view, node_detail

__all__ = ["graph_explorer_data", "build_graph_view", "node_detail"]


def graph_explorer_data(
    node: str | None = None,
    query: str | None = None,
    limit: int = 75,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Return nodes and edges for the System reference graph (vis-network ready)."""
    graph = load_graph(settings=settings or load_settings())
    return build_graph_view(graph, node=node, query=query, limit=limit)
