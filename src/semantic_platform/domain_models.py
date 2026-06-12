"""Domain model assembly and drop-in domain import.

A *domain model* groups the three split assets a knowledge architect supplies —
an ontology (``owl:Ontology``), SHACL shapes, and R2RML mappings — back into a
single view, even though they live in separate configured directories. Grouping
is by namespace: a class, property, shape target, or mapping output whose IRI
falls under a domain's ontology namespace belongs to that domain. Assets that
match no declared ontology land in a synthetic "Shared / Core" bucket so nothing
is silently dropped.

Authoring new domain content is handled by the governed Studio flow (ADR-0016);
this module only assembles the read-only grouped view.
"""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.mappings import MappingRecord, discover_mapping_files, list_mappings
from semantic_platform.ontology_version import ontology_metadata
from semantic_platform.r2rdf import MAP, RR, load_r2rml_mapping
from semantic_platform.shapes import ShapeRecord, list_shapes

SHARED_LABEL = "Shared / Core"


@dataclass(frozen=True)
class DomainModel:
    """A domain grouped from its ontology, shapes, and mappings."""

    ontology_iri: str
    label: str
    namespace: str
    version: str
    class_count: int
    property_count: int
    classes: tuple[str, ...]
    properties: tuple[str, ...]
    shapes: tuple[ShapeRecord, ...]
    mappings: tuple[MappingRecord, ...]
    is_shared: bool


def _base(iri: str) -> str:
    """Return the namespace base for an ontology IRI (trailing ``#``/``/`` stripped)."""
    return iri.rstrip("#/")


def _belongs(term: str, base: str) -> bool:
    """Return whether ``term`` falls under namespace ``base``."""
    return term == base or term.startswith(base + "#") or term.startswith(base + "/")


def _assign(term: str, bases: list[tuple[str, str]]) -> str | None:
    """Return the ontology IRI owning ``term``, preferring the most specific (longest) base."""
    best: tuple[str, str] | None = None
    for iri, base in bases:
        if _belongs(term, base) and (best is None or len(base) > len(best[1])):
            best = (iri, base)
    return best[0] if best else None


def _label(graph: Graph, node: URIRef, fallback: str) -> str:
    label = graph.value(node, RDFS.label)
    if label is not None:
        return str(label)
    local = fallback.rstrip("#/").rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    return local or fallback


def _mapping_terms(settings: Settings) -> dict[str, set[str]]:
    """Map each mapping IRI to the set of class and predicate IRIs it produces."""
    terms: dict[str, set[str]] = {}
    for path in discover_mapping_files(settings):
        graph = load_r2rml_mapping(path)
        for triples_map in set(graph.subjects(RDF.type, RR.TriplesMap)) | set(
            graph.subjects(RDF.type, MAP.Mapping)
        ):
            collected: set[str] = set()
            for subject_map in graph.objects(triples_map, RR.subjectMap):
                collected.update(str(c) for c in graph.objects(subject_map, RR["class"]))
            for pom in graph.objects(triples_map, RR.predicateObjectMap):
                collected.update(str(p) for p in graph.objects(pom, RR.predicate))
            terms[str(triples_map)] = collected
    return terms


def list_domain_models(settings: Settings | None = None) -> list[DomainModel]:
    """Group ontology classes/properties, shapes, and mappings into domain models."""
    settings = settings or load_settings()
    graph = load_graph(settings=settings)
    ontologies = ontology_metadata(settings=settings, graph=graph)
    bases = [(record.ontology, _base(record.ontology)) for record in ontologies]
    versions = {record.ontology: record.version for record in ontologies}

    classes = sorted(
        {str(c) for c in graph.subjects(RDF.type, OWL.Class)}
        | {str(c) for c in graph.subjects(RDF.type, RDFS.Class)}
    )
    properties = sorted(
        {str(p) for p in graph.subjects(RDF.type, OWL.ObjectProperty)}
        | {str(p) for p in graph.subjects(RDF.type, OWL.DatatypeProperty)}
        | {str(p) for p in graph.subjects(RDF.type, RDF.Property)}
    )
    shapes = list_shapes(settings)
    mappings = list_mappings(settings)
    mapping_terms = _mapping_terms(settings)

    buckets: dict[str | None, dict[str, list]] = {}

    def bucket(key: str | None) -> dict[str, list]:
        return buckets.setdefault(key, {"classes": [], "properties": [], "shapes": [], "mappings": []})

    for cls in classes:
        bucket(_assign(cls, bases))["classes"].append(cls)
    for prop in properties:
        bucket(_assign(prop, bases))["properties"].append(prop)
    for shape in shapes:
        owner = _assign(shape.target_class, bases) if shape.target_class else None
        bucket(owner)["shapes"].append(shape)
    for mapping in mappings:
        owner: str | None = None
        for term in sorted(mapping_terms.get(mapping.iri, set())):
            owner = _assign(term, bases)
            if owner is not None:
                break
        bucket(owner)["mappings"].append(mapping)

    models: list[DomainModel] = []
    for iri, base in sorted(bases, key=lambda pair: pair[0]):
        data = buckets.get(iri, {"classes": [], "properties": [], "shapes": [], "mappings": []})
        models.append(
            DomainModel(
                ontology_iri=iri,
                label=_label(graph, URIRef(iri), iri),
                namespace=base,
                version=versions.get(iri, ""),
                class_count=len(data["classes"]),
                property_count=len(data["properties"]),
                classes=tuple(data["classes"]),
                properties=tuple(data["properties"]),
                shapes=tuple(data["shapes"]),
                mappings=tuple(data["mappings"]),
                is_shared=False,
            )
        )

    shared = buckets.get(None)
    if shared and any(shared.values()):
        models.append(
            DomainModel(
                ontology_iri="",
                label=SHARED_LABEL,
                namespace="",
                version="",
                class_count=len(shared["classes"]),
                property_count=len(shared["properties"]),
                classes=tuple(shared["classes"]),
                properties=tuple(shared["properties"]),
                shapes=tuple(shared["shapes"]),
                mappings=tuple(shared["mappings"]),
                is_shared=True,
            )
        )
    return models
