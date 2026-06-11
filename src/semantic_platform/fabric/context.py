"""Enterprise context layer for humans, agents, applications, and workflows."""

from __future__ import annotations

from dataclasses import dataclass
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.fabric.common import EX, FABRIC, bind, label, local_id, text


@dataclass(frozen=True)
class EnterpriseContext:
    context_id: str
    uri: str
    label: str
    context_type: str
    scope: str
    governed_by: str


class ContextLayer:
    """Provides contextual grounding across platform execution surfaces."""

    CONTEXT_TYPES = {"organizational", "operational", "semantic", "execution", "agent"}

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph or load_graph([self.settings.vocabularies_dir, self.settings.data_dir], self.settings)
        bind(self.graph)

    def create_context(self, label_: str, *, context_type: str, scope: str = "enterprise") -> EnterpriseContext:
        if context_type not in self.CONTEXT_TYPES:
            raise ValueError(f"unsupported context type: {context_type}")
        context = URIRef(EX[f"context-{label_.lower().replace(' ', '-')}"])
        self.graph.add((context, RDF.type, FABRIC.ContextModel))
        self.graph.add((context, RDFS.label, Literal(label_)))
        self.graph.add((context, FABRIC.contextType, Literal(context_type)))
        self.graph.add((context, FABRIC.scope, Literal(scope)))
        return self._record(context)

    def list_contexts(self) -> list[EnterpriseContext]:
        return [self._record(node) for node in sorted(set(self.graph.subjects(RDF.type, FABRIC.ContextModel)), key=str)]

    def _record(self, context: URIRef) -> EnterpriseContext:
        governed = self.graph.value(context, FABRIC.governedBy)
        return EnterpriseContext(local_id(context), str(context), label(self.graph, context), text(self.graph, context, FABRIC.contextType), text(self.graph, context, FABRIC.scope), label(self.graph, governed) if isinstance(governed, URIRef) else str(governed or ""))
