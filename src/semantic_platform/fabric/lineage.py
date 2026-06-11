"""Enterprise lineage helpers for knowledge products, consumers, decisions, and execution."""

from __future__ import annotations

from dataclasses import dataclass
from rdflib import Graph, URIRef

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.fabric.common import PROV, bind, label, local_id


@dataclass(frozen=True)
class LineageEdge:
    source: str
    target: str
    relation: str


class EnterpriseLineage:
    """Read PROV-O lineage across the enterprise knowledge fabric."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph or load_graph([self.settings.vocabularies_dir, self.settings.data_dir], self.settings)
        bind(self.graph)

    def edges(self) -> list[LineageEdge]:
        predicates = [PROV.wasDerivedFrom, PROV.wasGeneratedBy, PROV.used, PROV.wasAssociatedWith]
        rows: list[LineageEdge] = []
        for predicate in predicates:
            for source, _, target in self.graph.triples((None, predicate, None)):
                if isinstance(source, URIRef) and isinstance(target, URIRef):
                    rows.append(LineageEdge(label(self.graph, source), label(self.graph, target), local_id(predicate)))
        return rows
