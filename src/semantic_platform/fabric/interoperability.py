"""Enterprise semantic interoperability services."""

from __future__ import annotations

from dataclasses import dataclass
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.fabric.common import FABRIC, bind, label, local_id
from semantic_platform.fabric.contracts import ContractRegistry


@dataclass(frozen=True)
class SemanticMapping:
    mapping_id: str
    uri: str
    label: str
    source: str
    target: str
    relation: str


class InteroperabilityLayer:
    """Validate mappings, align vocabularies, and score semantic interoperability."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph or load_graph([self.settings.vocabularies_dir, self.settings.data_dir], self.settings)
        bind(self.graph)

    def list_mappings(self) -> list[SemanticMapping]:
        nodes = set(self.graph.subjects(RDF.type, FABRIC.SemanticDependency)) | set(self.graph.subjects(SKOS.exactMatch, None))
        return [self._record(node) for node in sorted(nodes, key=str)]

    def validate_mappings(self) -> list[str]:
        errors: list[str] = []
        for mapping in self.list_mappings():
            if not mapping.source:
                errors.append(f"{mapping.mapping_id} is missing source")
            if not mapping.target:
                errors.append(f"{mapping.mapping_id} is missing target")
        return errors

    def validate_contracts(self) -> list[str]:
        return ContractRegistry(graph=self.graph, settings=self.settings).validate_contracts()

    def interoperability_score(self) -> float:
        mappings = self.list_mappings()
        contracts = ContractRegistry(graph=self.graph, settings=self.settings)
        mapping_score = 1.0 if mappings and not self.validate_mappings() else 0.0
        return round((mapping_score + contracts.compatibility_coverage()) / 2, 4)

    def _record(self, node: URIRef) -> SemanticMapping:
        target = self.graph.value(node, SKOS.exactMatch) or self.graph.value(node, FABRIC.dependsOn)
        source = self.graph.value(node, FABRIC.sourceConcept) or node
        return SemanticMapping(local_id(node), str(node), label(self.graph, node), label(self.graph, source) if isinstance(source, URIRef) else str(source or ""), label(self.graph, target) if isinstance(target, URIRef) else str(target or ""), "exactMatch" if (node, SKOS.exactMatch, None) in self.graph else "dependsOn")
