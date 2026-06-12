"""Tests for deterministic model scaffolding."""

from __future__ import annotations

from rdflib import Graph

from semantic_platform.authoring.scaffold import InterviewAnswers, scaffold_model


def _answers(**kw) -> InterviewAnswers:
    base = dict(
        domain_label="Field Service",
        prefix="fs",
        base_namespace="https://example.org/fs#",
        classes=("Technician", "Work Order"),
        properties=(("assignedTo", "Work Order", "Technician"), ("priority", "Work Order", "xsd:string")),
    )
    base.update(kw)
    return InterviewAnswers(**base)


def test_scaffold_produces_expected_files():
    plan = scaffold_model(_answers())
    assert set(plan.files) == {
        "rdf/ontology/ontology.ttl",
        "rdf/shapes/domain_shapes.ttl",
        "rdf/data/sample.ttl",
    }


def test_generated_turtle_is_valid_and_well_formed():
    plan = scaffold_model(_answers())
    for path, content in plan.files.items():
        graph = Graph()
        graph.parse(data=content, format="turtle")  # raises on syntax error
        assert len(graph) > 0, path
    ontology = plan.files["rdf/ontology/ontology.ttl"]
    assert "fs:WorkOrder a owl:Class" in ontology
    assert "fs:assignedTo a owl:ObjectProperty" in ontology
    assert "fs:priority a owl:DatatypeProperty" in ontology
    assert "rdfs:range xsd:string" in ontology


def test_toggles_omit_shapes_and_data():
    plan = scaffold_model(_answers(include_shapes=False, include_sample_data=False))
    assert set(plan.files) == {"rdf/ontology/ontology.ttl"}


def test_no_classes_yields_only_ontology():
    plan = scaffold_model(_answers(classes=(), properties=()))
    assert set(plan.files) == {"rdf/ontology/ontology.ttl"}
