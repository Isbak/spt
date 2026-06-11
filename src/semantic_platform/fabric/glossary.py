"""Enterprise glossary based on SKOS patterns."""

from __future__ import annotations

from dataclasses import dataclass
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.fabric.common import FABRIC, GOV, bind, label, local_id


@dataclass(frozen=True)
class GlossaryTerm:
    term_id: str
    uri: str
    pref_label: str
    definition: str
    synonyms: tuple[str, ...]
    owner: str
    lifecycle_state: str


class Glossary:
    """Manage business glossary terms and lifecycle metadata."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph or load_graph([self.settings.vocabularies_dir, self.settings.data_dir], self.settings)
        bind(self.graph)

    def list_terms(self) -> list[GlossaryTerm]:
        return [self._record(node) for node in sorted(set(self.graph.subjects(RDF.type, SKOS.Concept)), key=str) if (node, RDF.type, FABRIC.EnterpriseConcept) in self.graph or self.graph.value(node, SKOS.definition)]

    def add_term(self, uri: str, label_: str, definition: str, *, owner: str, synonyms: tuple[str, ...] = ()) -> GlossaryTerm:
        term = URIRef(uri)
        self.graph.add((term, RDF.type, SKOS.Concept))
        self.graph.add((term, RDF.type, FABRIC.EnterpriseConcept))
        self.graph.add((term, SKOS.prefLabel, Literal(label_)))
        self.graph.add((term, SKOS.definition, Literal(definition)))
        self.graph.add((term, FABRIC.ownedBy, Literal(owner)))
        self.graph.add((term, FABRIC.lifecycleState, Literal("Active")))
        for synonym in synonyms:
            self.graph.add((term, SKOS.altLabel, Literal(synonym)))
        return self._record(term)

    def validate_terms(self) -> list[str]:
        errors = []
        for term in self.list_terms():
            if not term.pref_label:
                errors.append(f"{term.term_id} is missing preferred label")
            if not term.definition:
                errors.append(f"{term.term_id} is missing definition")
            if not term.owner:
                errors.append(f"{term.term_id} is missing owner")
        return errors

    def _record(self, term: URIRef) -> GlossaryTerm:
        owner_node = self.graph.value(term, FABRIC.ownedBy) or self.graph.value(term, GOV.hasOwner)
        pref = self.graph.value(term, SKOS.prefLabel)
        definition = self.graph.value(term, SKOS.definition)
        return GlossaryTerm(local_id(term), str(term), str(pref or label(self.graph, term)), str(definition or ""), tuple(str(v) for v in self.graph.objects(term, SKOS.altLabel)), label(self.graph, owner_node) if isinstance(owner_node, URIRef) else str(owner_node or ""), str(self.graph.value(term, FABRIC.lifecycleState) or ""))
