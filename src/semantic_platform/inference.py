"""Inference generation and inferred graph management."""

from __future__ import annotations

from dataclasses import dataclass, field
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

from semantic_platform.explanation import Explanation, Triple
from semantic_platform.rule_registry import REASON, Rule

EX = Namespace("https://example.org/semantic-platform/example#")

BUILTIN_RDFS_RULE = REASON["rule-rdfs-core"]
BUILTIN_OWL_RULE = REASON["rule-owl-compatible-patterns"]
BUILTIN_GENERIC_RULE = REASON["rule-contributes-to-dataset"]


@dataclass
class InferenceResult:
    """Result of an inference pass."""

    inferred_graph: Graph = field(default_factory=Graph)
    explanations: list[Explanation] = field(default_factory=list)

    @property
    def triple_count(self) -> int:
        """Return inferred triple count."""
        return len(self.inferred_graph)

    def add(self, assertion: Triple, rule: URIRef, sources: tuple[Triple, ...], engine_version: str) -> bool:
        """Add an inferred triple and explanation if the assertion is new for this pass."""
        if assertion in self.inferred_graph:
            return False
        self.inferred_graph.add(assertion)
        self.explanations.append(Explanation(assertion, rule, sources, engine_version))
        return True


def _uri_objects(graph: Graph, subject: URIRef, predicate: URIRef) -> list[URIRef]:
    return [value for value in graph.objects(subject, predicate) if isinstance(value, URIRef)]


def infer_rdfs(graph: Graph, result: InferenceResult, engine_version: str) -> None:
    """Infer RDFS subclass, type-inheritance, and subproperty assertions."""
    changed = True
    while changed:
        changed = False
        union = graph + result.inferred_graph
        for subclass in set(union.subjects(RDFS.subClassOf, None)):
            if not isinstance(subclass, URIRef):
                continue
            for parent in _uri_objects(union, subclass, RDFS.subClassOf):
                for ancestor in _uri_objects(union, parent, RDFS.subClassOf):
                    assertion = (subclass, RDFS.subClassOf, ancestor)
                    changed |= result.add(
                        assertion,
                        BUILTIN_RDFS_RULE,
                        ((subclass, RDFS.subClassOf, parent), (parent, RDFS.subClassOf, ancestor)),
                        engine_version,
                    )
        union = graph + result.inferred_graph
        for instance, cls in set(union.subject_objects(RDF.type)):
            if not isinstance(instance, URIRef) or not isinstance(cls, URIRef):
                continue
            for parent in _uri_objects(union, cls, RDFS.subClassOf):
                assertion = (instance, RDF.type, parent)
                changed |= result.add(
                    assertion,
                    BUILTIN_RDFS_RULE,
                    ((instance, RDF.type, cls), (cls, RDFS.subClassOf, parent)),
                    engine_version,
                )
        union = graph + result.inferred_graph
        for prop in set(union.subjects(RDFS.subPropertyOf, None)):
            if not isinstance(prop, URIRef):
                continue
            for super_prop in _uri_objects(union, prop, RDFS.subPropertyOf):
                for subject, obj in set(union.subject_objects(prop)):
                    if isinstance(subject, URIRef) and isinstance(obj, URIRef):
                        assertion = (subject, super_prop, obj)
                        changed |= result.add(
                            assertion,
                            BUILTIN_RDFS_RULE,
                            ((prop, RDFS.subPropertyOf, super_prop), (subject, prop, obj)),
                            engine_version,
                        )


def infer_owl_patterns(graph: Graph, result: InferenceResult, engine_version: str) -> None:
    """Infer practical OWL-compatible patterns without full OWL DL reasoning."""
    changed = True
    while changed:
        changed = False
        union = graph + result.inferred_graph
        for left, right in set(union.subject_objects(OWL.equivalentClass)):
            if isinstance(left, URIRef) and isinstance(right, URIRef):
                for assertion, sources in [
                    ((left, RDFS.subClassOf, right), ((left, OWL.equivalentClass, right),)),
                    ((right, RDFS.subClassOf, left), ((left, OWL.equivalentClass, right),)),
                ]:
                    changed |= result.add(assertion, BUILTIN_OWL_RULE, sources, engine_version)
                for instance in set(union.subjects(RDF.type, left)):
                    if isinstance(instance, URIRef):
                        changed |= result.add(
                            (instance, RDF.type, right),
                            BUILTIN_OWL_RULE,
                            ((left, OWL.equivalentClass, right), (instance, RDF.type, left)),
                            engine_version,
                        )
        union = graph + result.inferred_graph
        for left, right in set(union.subject_objects(OWL.equivalentProperty)):
            if isinstance(left, URIRef) and isinstance(right, URIRef):
                for s, o in set(union.subject_objects(left)):
                    if isinstance(s, URIRef) and isinstance(o, URIRef):
                        changed |= result.add((s, right, o), BUILTIN_OWL_RULE, ((left, OWL.equivalentProperty, right), (s, left, o)), engine_version)
                for s, o in set(union.subject_objects(right)):
                    if isinstance(s, URIRef) and isinstance(o, URIRef):
                        changed |= result.add((s, left, o), BUILTIN_OWL_RULE, ((left, OWL.equivalentProperty, right), (s, right, o)), engine_version)
        union = graph + result.inferred_graph
        for prop, inverse in set(union.subject_objects(OWL.inverseOf)):
            if isinstance(prop, URIRef) and isinstance(inverse, URIRef):
                for s, o in set(union.subject_objects(prop)):
                    if isinstance(s, URIRef) and isinstance(o, URIRef):
                        changed |= result.add((o, inverse, s), BUILTIN_OWL_RULE, ((prop, OWL.inverseOf, inverse), (s, prop, o)), engine_version)
                for s, o in set(union.subject_objects(inverse)):
                    if isinstance(s, URIRef) and isinstance(o, URIRef):
                        changed |= result.add((o, prop, s), BUILTIN_OWL_RULE, ((prop, OWL.inverseOf, inverse), (s, inverse, o)), engine_version)
        union = graph + result.inferred_graph
        for prop in set(union.subjects(RDF.type, OWL.SymmetricProperty)):
            if isinstance(prop, URIRef):
                for s, o in set(union.subject_objects(prop)):
                    if isinstance(s, URIRef) and isinstance(o, URIRef):
                        changed |= result.add((o, prop, s), BUILTIN_OWL_RULE, ((prop, RDF.type, OWL.SymmetricProperty), (s, prop, o)), engine_version)
        union = graph + result.inferred_graph
        for prop in set(union.subjects(RDF.type, OWL.TransitiveProperty)):
            if isinstance(prop, URIRef):
                for a, b in set(union.subject_objects(prop)):
                    if not isinstance(a, URIRef) or not isinstance(b, URIRef):
                        continue
                    for c in _uri_objects(union, b, prop):
                        changed |= result.add((a, prop, c), BUILTIN_OWL_RULE, ((prop, RDF.type, OWL.TransitiveProperty), (a, prop, b), (b, prop, c)), engine_version)


def infer_rules(graph: Graph, result: InferenceResult, rules: list[Rule], engine_version: str) -> None:
    """Execute generic platform rules."""
    executable = {rule.iri for rule in rules}
    if BUILTIN_GENERIC_RULE not in executable:
        return
    person = EX.Person
    org = EX.Organization
    dataset = EX.Dataset
    employed_by = EX.employedBy
    owns = EX.owns
    contributes_to = EX.contributesTo
    for employee in set(graph.subjects(RDF.type, person)):
        if not isinstance(employee, URIRef):
            continue
        for organization in _uri_objects(graph, employee, employed_by):
            if (organization, RDF.type, org) not in graph:
                continue
            for data_asset in _uri_objects(graph, organization, owns):
                if (data_asset, RDF.type, dataset) not in graph:
                    continue
                result.add(
                    (employee, contributes_to, data_asset),
                    BUILTIN_GENERIC_RULE,
                    ((employee, RDF.type, person), (employee, employed_by, organization), (organization, RDF.type, org), (organization, owns, data_asset), (data_asset, RDF.type, dataset)),
                    engine_version,
                )
