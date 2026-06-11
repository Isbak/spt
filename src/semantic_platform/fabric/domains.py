"""Knowledge domain registry for the Enterprise Knowledge Fabric."""

from __future__ import annotations

from dataclasses import dataclass
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.fabric.common import EX, FABRIC, GOV, bind, label, labels, local_id


@dataclass(frozen=True)
class KnowledgeDomain:
    domain_id: str
    uri: str
    label: str
    owner: str
    steward: str
    responsibilities: tuple[str, ...]
    products: tuple[str, ...]
    governed_by: tuple[str, ...]


class DomainRegistry:
    """Read and register governed enterprise knowledge domains."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph or load_graph([self.settings.vocabularies_dir, self.settings.data_dir], self.settings)
        bind(self.graph)

    def register_domain(self, label_: str, *, owner: str, steward: str, responsibilities: tuple[str, ...] = ()) -> KnowledgeDomain:
        domain = URIRef(EX[f"domain-{label_.lower().replace(' ', '-')}"])
        self.graph.add((domain, RDF.type, FABRIC.KnowledgeDomain))
        self.graph.add((domain, RDFS.label, Literal(label_)))
        self.graph.add((domain, FABRIC.ownedBy, Literal(owner)))
        self.graph.add((domain, GOV.hasSteward, Literal(steward)))
        for responsibility in responsibilities:
            self.graph.add((domain, FABRIC.responsibility, Literal(responsibility)))
        return self._record(domain)

    def list_domains(self) -> list[KnowledgeDomain]:
        return [self._record(node) for node in sorted(set(self.graph.subjects(RDF.type, FABRIC.KnowledgeDomain)), key=str)]

    def validate_ownership(self) -> list[str]:
        errors: list[str] = []
        for domain in self.list_domains():
            if not domain.owner:
                errors.append(f"{domain.domain_id} is missing owner")
            if not domain.steward:
                errors.append(f"{domain.domain_id} is missing steward")
        if not self.list_domains():
            errors.append("no knowledge domains registered")
        return errors

    def _record(self, domain: URIRef) -> KnowledgeDomain:
        products = labels(self.graph, domain, FABRIC.produces)
        governed_by = labels(self.graph, domain, FABRIC.governedBy)
        responsibilities = tuple(str(v) for v in self.graph.objects(domain, FABRIC.responsibility))
        owner_node = self.graph.value(domain, FABRIC.ownedBy) or self.graph.value(domain, GOV.hasOwner)
        steward_node = self.graph.value(domain, GOV.hasSteward)
        return KnowledgeDomain(
            domain_id=local_id(domain),
            uri=str(domain),
            label=label(self.graph, domain),
            owner=label(self.graph, owner_node) if isinstance(owner_node, URIRef) else str(owner_node or ""),
            steward=label(self.graph, steward_node) if isinstance(steward_node, URIRef) else str(steward_node or ""),
            responsibilities=responsibilities,
            products=products,
            governed_by=governed_by,
        )
