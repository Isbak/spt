"""Semantic contract management for cross-domain interoperability."""

from __future__ import annotations

from dataclasses import dataclass
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.fabric.common import CONTRACT, EX, FABRIC, bind, label, local_id, text


@dataclass(frozen=True)
class SemanticContract:
    contract_id: str
    uri: str
    label: str
    producer: str
    consumer: str
    version: str
    lifecycle_state: str
    compatibility: str


class ContractRegistry:
    """Registry and validator for semantic contracts."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph or load_graph([self.settings.vocabularies_dir, self.settings.data_dir], self.settings)
        bind(self.graph)

    def register_contract(self, label_: str, *, producer: str, consumer: str, version: str = "1.0.0", compatibility: str = "Compatible") -> SemanticContract:
        contract = URIRef(EX[f"contract-{label_.lower().replace(' ', '-')}"])
        self.graph.add((contract, RDF.type, CONTRACT.SemanticContract))
        self.graph.add((contract, RDF.type, FABRIC.SemanticContract))
        self.graph.add((contract, RDFS.label, Literal(label_)))
        self.graph.add((contract, CONTRACT.producer, Literal(producer)))
        self.graph.add((contract, CONTRACT.consumer, Literal(consumer)))
        self.graph.add((contract, CONTRACT.version, Literal(version)))
        self.graph.add((contract, CONTRACT.lifecycleState, Literal("Active")))
        self.graph.add((contract, CONTRACT.compatibility, Literal(compatibility)))
        return self._record(contract)

    def list_contracts(self) -> list[SemanticContract]:
        nodes = set(self.graph.subjects(RDF.type, CONTRACT.SemanticContract)) | set(self.graph.subjects(RDF.type, FABRIC.SemanticContract))
        return [self._record(node) for node in sorted(nodes, key=str)]

    def validate_contracts(self) -> list[str]:
        errors: list[str] = []
        for contract in self.list_contracts():
            for field in ("producer", "consumer", "version", "lifecycle_state", "compatibility"):
                if not getattr(contract, field):
                    errors.append(f"{contract.contract_id} is missing {field}")
        return errors

    def compatibility_coverage(self) -> float:
        contracts = self.list_contracts()
        if not contracts:
            return 1.0
        compatible = sum(1 for c in contracts if c.compatibility in {"Compatible", "BackwardCompatible", "ForwardCompatible"})
        return round(compatible / len(contracts), 4)

    def _record(self, contract: URIRef) -> SemanticContract:
        producer = self.graph.value(contract, CONTRACT.producer) or self.graph.value(contract, FABRIC.produces)
        consumer = self.graph.value(contract, CONTRACT.consumer) or self.graph.value(contract, FABRIC.consumes)
        return SemanticContract(
            contract_id=local_id(contract),
            uri=str(contract),
            label=label(self.graph, contract),
            producer=label(self.graph, producer) if isinstance(producer, URIRef) else str(producer or ""),
            consumer=label(self.graph, consumer) if isinstance(consumer, URIRef) else str(consumer or ""),
            version=text(self.graph, contract, CONTRACT.version) or text(self.graph, contract, FABRIC.version),
            lifecycle_state=text(self.graph, contract, CONTRACT.lifecycleState) or text(self.graph, contract, FABRIC.lifecycleState),
            compatibility=text(self.graph, contract, CONTRACT.compatibility),
        )
