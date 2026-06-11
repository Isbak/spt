"""Federation framework for domains, products, ontologies, and graphs."""

from __future__ import annotations

from dataclasses import dataclass
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.fabric.common import FABRIC, bind, label, labels, local_id


@dataclass(frozen=True)
class FederatedGraph:
    federation_id: str
    uri: str
    label: str
    domains: tuple[str, ...]
    products: tuple[str, ...]
    graphs: tuple[str, ...]
    ontologies: tuple[str, ...]
    federates_with: tuple[str, ...]


class FederationRegistry:
    """Discover and describe federated enterprise graph relationships."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph or load_graph([self.settings.vocabularies_dir, self.settings.data_dir, self.settings.graphs_dir], self.settings)
        bind(self.graph)

    def list_federations(self) -> list[FederatedGraph]:
        return [self._record(node) for node in sorted(set(self.graph.subjects(RDF.type, FABRIC.Federation)), key=str)]

    def discover_for_domain(self, domain_label: str) -> list[FederatedGraph]:
        return [fed for fed in self.list_federations() if domain_label in fed.domains or domain_label in fed.label]

    def federated_graph_count(self) -> int:
        return sum(len(fed.graphs) for fed in self.list_federations())

    def _record(self, federation: URIRef) -> FederatedGraph:
        return FederatedGraph(
            federation_id=local_id(federation),
            uri=str(federation),
            label=label(self.graph, federation),
            domains=labels(self.graph, federation, FABRIC.consumes),
            products=labels(self.graph, federation, FABRIC.produces),
            graphs=labels(self.graph, federation, FABRIC.federatesWith),
            ontologies=labels(self.graph, federation, FABRIC.usesOntology),
            federates_with=labels(self.graph, federation, FABRIC.federatesWith),
        )
