"""Shared semantic memory represented as RDF resources."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, RDFS

from semantic_platform.multi_agent.common import MA, add_prov_activity, bind, now_literal, text


class MemoryType(StrEnum):
    WORKING = "SharedWorkingMemory"
    KNOWLEDGE = "SharedKnowledgeMemory"
    DECISION = "SharedDecisionMemory"


@dataclass(frozen=True)
class MemoryRecord:
    uri: str
    memory_type: str
    label: str
    content: str
    references: tuple[str, ...]


class SharedSemanticMemory:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        bind(self.graph)

    def write(self, memory_type: MemoryType | str, label: str, content: str, *, actor: str, references: tuple[str, ...] = ()) -> MemoryRecord:
        kind = str(memory_type.value if isinstance(memory_type, MemoryType) else memory_type)
        memory = URIRef(MA[f"memory-{kind.lower()}-{len(list(self.graph.subjects(RDF.type, MA.SharedSemanticMemory))) + 1}"])
        type_uri = URIRef(MA[kind])
        self.graph.add((memory, RDF.type, MA.SharedSemanticMemory))
        self.graph.add((memory, RDF.type, type_uri))
        self.graph.add((memory, RDFS.label, Literal(label)))
        self.graph.add((memory, MA.memoryContent, Literal(content)))
        self.graph.add((memory, PROV.generatedAtTime, now_literal()))
        for ref in references:
            self.graph.add((memory, MA.referencesSemanticAsset, URIRef(ref) if ref.startswith("http") else URIRef(MA[ref])))
        add_prov_activity(self.graph, MA.MemoryActivity, "Write shared semantic memory", actor, generated=memory)
        return self._record(memory)

    def list_memory(self) -> list[MemoryRecord]:
        return [self._record(m) for m in self.graph.subjects(RDF.type, MA.SharedSemanticMemory)]

    def _record(self, memory: URIRef) -> MemoryRecord:
        types = [str(t).rsplit("#", 1)[-1] for t in self.graph.objects(memory, RDF.type) if str(t).startswith(str(MA)) and t != MA.SharedSemanticMemory]
        return MemoryRecord(str(memory), types[0] if types else "SharedSemanticMemory", text(self.graph, memory, RDFS.label), text(self.graph, memory, MA.memoryContent), tuple(str(r) for r in self.graph.objects(memory, MA.referencesSemanticAsset)))
