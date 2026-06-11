"""Execution registry helpers over RDF registry data."""

from __future__ import annotations

from rdflib import Graph

from semantic_platform.execution.actions import ActionCatalog, ExecutionActionRecord
from semantic_platform.execution.common import bind


class ExecutionRegistry:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())
        self.catalog = ActionCatalog(self.graph)

    def list_actions(self) -> list[ExecutionActionRecord]:
        return self.catalog.list_actions()

    def approved_actions(self) -> list[ExecutionActionRecord]:
        return [a for a in self.list_actions() if a.status == "Approved"]
