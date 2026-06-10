from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

from semantic_platform.consistency import validate_consistency
from semantic_platform.inference import BUILTIN_GENERIC_RULE
from semantic_platform.reasoning import INFERRED_GRAPH, REASONING_GRAPH, VALIDATION_GRAPH, run_reasoning
from semantic_platform.rule_registry import Rule, RuleRegistry, load_rule_registry

EX = Namespace("https://example.org/semantic-platform/example#")
REASON = Namespace("https://example.org/semantic-platform/reasoning#")
GOV = Namespace("https://example.org/semantic-platform/governance#")


def sample_graph():
    g = Graph()
    g.add((EX.A, RDFS.subClassOf, EX.B))
    g.add((EX.B, RDFS.subClassOf, EX.C))
    g.add((EX.instance, RDF.type, EX.A))
    g.add((EX.childProp, RDFS.subPropertyOf, EX.parentProp))
    g.add((EX.s, EX.childProp, EX.o))
    g.add((EX.DataProduct, OWL.equivalentClass, EX.Dataset))
    g.add((EX.dp1, RDF.type, EX.DataProduct))
    g.add((EX.p, OWL.equivalentProperty, EX.q))
    g.add((EX.left, EX.p, EX.right))
    g.add((EX.owns, OWL.inverseOf, EX.ownedBy))
    g.add((EX.org, EX.owns, EX.asset))
    g.add((EX.connectedTo, RDF.type, OWL.SymmetricProperty))
    g.add((EX.node1, EX.connectedTo, EX.node2))
    g.add((EX.partOf, RDF.type, OWL.TransitiveProperty))
    g.add((EX.part1, EX.partOf, EX.part2))
    g.add((EX.part2, EX.partOf, EX.part3))
    g.add((EX.Person, RDF.type, OWL.Class))
    g.add((EX.Organization, RDF.type, OWL.Class))
    g.add((EX.Dataset, RDF.type, OWL.Class))
    g.add((EX.person, RDF.type, EX.Person))
    g.add((EX.person, EX.employedBy, EX.organization))
    g.add((EX.organization, RDF.type, EX.Organization))
    g.add((EX.organization, EX.owns, EX.dataset))
    g.add((EX.dataset, RDF.type, EX.Dataset))
    for rule in [REASON["rule-rdfs-core"], REASON["rule-owl-compatible-patterns"], BUILTIN_GENERIC_RULE]:
        g.add((rule, RDF.type, REASON.Rule))
        g.add((rule, RDFS.label, rule))
        g.add((rule, REASON.ruleOwner, GOV.platformOwner))
        g.add((rule, REASON.ruleSteward, GOV.platformSteward))
        g.add((rule, REASON.ruleStatus, REASON.Approved))
        g.add((rule, OWL.versionInfo, URIRef("urn:version:1")))
    return g


def test_rdfs_and_owl_compatible_reasoning_patterns():
    run = run_reasoning(graph=sample_graph())
    inferred = run.inferred_graph
    assert (EX.A, RDFS.subClassOf, EX.C) in inferred
    assert (EX.instance, RDF.type, EX.B) in inferred
    assert (EX.s, EX.parentProp, EX.o) in inferred
    assert (EX.dp1, RDF.type, EX.Dataset) in inferred
    assert (EX.left, EX.q, EX.right) in inferred
    assert (EX.asset, EX.ownedBy, EX.org) in inferred
    assert (EX.node2, EX.connectedTo, EX.node1) in inferred
    assert (EX.part1, EX.partOf, EX.part3) in inferred


def test_rule_execution_explanations_and_provenance():
    run = run_reasoning(graph=sample_graph())
    assert (EX.person, EX.contributesTo, EX.dataset) in run.inferred_graph
    assert run.explanation_count >= 1
    assert any("rule-contributes-to-dataset" in rule for rule in run.rules_used)
    assert len(list(run.reasoning_graph.subjects(RDF.type, REASON.Explanation))) >= 1
    assert len(list(run.reasoning_graph.subjects(RDF.type, REASON.ReasoningEngineExecution))) == 1
    assert {str(REASONING_GRAPH), str(INFERRED_GRAPH), str(VALIDATION_GRAPH)}


def test_rule_registry_lifecycle_blocks_deprecated_rules():
    approved = Rule(REASON.approvedRule, "Approved", "1", "owner", "steward", "Approved")
    deprecated = Rule(REASON.oldRule, "Old", "1", "owner", "steward", "Deprecated")
    registry = RuleRegistry([approved, deprecated])
    assert registry.executable() == [approved]
    registry.disable(approved.iri)
    assert registry.executable() == []
    registry.enable(approved.iri)
    assert registry.executable() == [approved]


def test_load_rule_registry_from_rdf_assets():
    registry = load_rule_registry()
    labels = {rule.label for rule in registry.all()}
    assert "Generic contribution inference" in labels
    assert all(rule.owner for rule in registry.all())


def test_consistency_validation_missing_type_broken_reference_and_cycle():
    g = Graph()
    g.add((EX.untyped, EX.pointsTo, EX.missing))
    g.add((EX.A, RDFS.subClassOf, EX.B))
    g.add((EX.B, RDFS.subClassOf, EX.A))
    report = validate_consistency(g)
    checks = {issue.check for issue in report.issues}
    assert "missing-types" in checks
    assert "broken-references" in checks
    assert "cyclic-structures" in checks
    assert not report.conforms
