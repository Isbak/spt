"""Knowledge product framework for managed semantic assets."""

from __future__ import annotations

from dataclasses import dataclass
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.fabric.common import EX, FABRIC, GOV, bind, label, labels, local_id, text


@dataclass(frozen=True)
class KnowledgeProduct:
    product_id: str
    uri: str
    label: str
    version: str
    owner: str
    lifecycle_state: str
    consumers: tuple[str, ...]
    dependencies: tuple[str, ...]
    contracts: tuple[str, ...]


class KnowledgeProductCatalog:
    """Catalog for product discovery, ownership, and lifecycle management."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph or load_graph([self.settings.vocabularies_dir, self.settings.data_dir], self.settings)
        bind(self.graph)

    def register_product(self, label_: str, *, owner: str, version: str = "1.0.0", lifecycle_state: str = "Active") -> KnowledgeProduct:
        product = URIRef(EX[f"product-{label_.lower().replace(' ', '-')}"])
        self.graph.add((product, RDF.type, FABRIC.KnowledgeProduct))
        self.graph.add((product, RDFS.label, Literal(label_)))
        self.graph.add((product, FABRIC.ownedBy, Literal(owner)))
        self.graph.add((product, FABRIC.version, Literal(version)))
        self.graph.add((product, FABRIC.lifecycleState, Literal(lifecycle_state)))
        return self._record(product)

    def list_products(self) -> list[KnowledgeProduct]:
        return [self._record(node) for node in sorted(set(self.graph.subjects(RDF.type, FABRIC.KnowledgeProduct)), key=str)]

    def dependencies_for(self, product_id: str) -> tuple[str, ...]:
        for product in self.list_products():
            if product.product_id == product_id or product.uri == product_id:
                return product.dependencies
        return ()

    def _record(self, product: URIRef) -> KnowledgeProduct:
        owner_node = self.graph.value(product, FABRIC.ownedBy) or self.graph.value(product, GOV.hasOwner)
        return KnowledgeProduct(
            product_id=local_id(product),
            uri=str(product),
            label=label(self.graph, product),
            version=text(self.graph, product, FABRIC.version),
            owner=label(self.graph, owner_node) if isinstance(owner_node, URIRef) else str(owner_node or ""),
            lifecycle_state=text(self.graph, product, FABRIC.lifecycleState),
            consumers=labels(self.graph, product, FABRIC.consumes),
            dependencies=labels(self.graph, product, FABRIC.dependsOn),
            contracts=labels(self.graph, product, FABRIC.exposesContract),
        )
