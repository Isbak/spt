"""Tests for domain model grouping by namespace."""

from __future__ import annotations

import dataclasses

from semantic_platform.config import Settings, load_settings
from semantic_platform.domain_models import list_domain_models

ONTOLOGY_TTL = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix d: <https://example.org/widget#> .

<https://example.org/widget> a owl:Ontology ;
    rdfs:label "Widget domain" ;
    owl:versionInfo "1.0.0" .

d:Widget a owl:Class ; rdfs:label "Widget" .
d:weight a owl:DatatypeProperty ; rdfs:domain d:Widget .
"""

SHAPE_TTL = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix d: <https://example.org/widget#> .

d:WidgetShape a sh:NodeShape ;
    sh:targetClass d:Widget ;
    sh:property [ sh:path d:weight ] .
"""

MAPPING_TTL = """
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix map: <https://example.org/semantic-platform/mappings#> .
@prefix gov: <https://example.org/semantic-platform/governance#> .
@prefix d: <https://example.org/widget#> .

<https://example.org/mapping/widget> a rr:TriplesMap, map:Mapping ;
    rr:logicalTable [ rr:tableName "widget" ] ;
    rr:subjectMap [ rr:template "https://example.org/widget/{id}" ; rr:class d:Widget ] ;
    rr:predicateObjectMap [ rr:predicate d:weight ; rr:objectMap [ rr:column "weight" ] ] ;
    map:sourcedFrom <https://example.org/source/widgets> ;
    map:targetGraph <urn:graph:masterdata> ;
    map:version "1.0.0" ;
    gov:hasOwner gov:platformOwner ;
    gov:hasSteward gov:platformSteward .
"""


def _settings(tmp_path) -> Settings:
    dirs = {}
    for name in ("ontology", "vocabularies", "data", "graphs", "shapes", "r2rml"):
        path = tmp_path / name
        path.mkdir()
        dirs[name] = path
    base = load_settings()
    return dataclasses.replace(
        base,
        ontology_dir=dirs["ontology"],
        vocabularies_dir=dirs["vocabularies"],
        data_dir=dirs["data"],
        graphs_dir=dirs["graphs"],
        shapes_dir=dirs["shapes"],
        r2rml_dir=dirs["r2rml"],
    )


def _seed(settings: Settings) -> None:
    (settings.ontology_dir / "widget.ttl").write_text(ONTOLOGY_TTL, encoding="utf-8")
    (settings.shapes_dir / "widget_shapes.ttl").write_text(SHAPE_TTL, encoding="utf-8")
    (settings.r2rml_dir / "widget.ttl").write_text(MAPPING_TTL, encoding="utf-8")


def test_grouping_associates_ontology_shapes_and_mappings(tmp_path):
    settings = _settings(tmp_path)
    _seed(settings)
    models = list_domain_models(settings)
    widget = next(m for m in models if m.ontology_iri == "https://example.org/widget")
    assert widget.version == "1.0.0"
    assert "https://example.org/widget#Widget" in widget.classes
    assert any(s.iri == "https://example.org/widget#WidgetShape" for s in widget.shapes)
    assert any(m.target_graph == "urn:graph:masterdata" for m in widget.mappings)
    assert not widget.is_shared


def test_longest_base_wins_for_overlapping_namespaces(tmp_path):
    settings = _settings(tmp_path)
    overlapping = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix a: <https://example.org/widget#> .
@prefix b: <https://example.org/widget/ext#> .

<https://example.org/widget> a owl:Ontology ; owl:versionInfo "1.0.0" .
<https://example.org/widget/ext> a owl:Ontology ; owl:versionInfo "1.0.0" .

a:Base a owl:Class .
b:Special a owl:Class .
"""
    (settings.ontology_dir / "overlap.ttl").write_text(overlapping, encoding="utf-8")
    models = {m.ontology_iri: m for m in list_domain_models(settings)}
    ext = models["https://example.org/widget/ext"]
    base = models["https://example.org/widget"]
    assert "https://example.org/widget/ext#Special" in ext.classes
    assert "https://example.org/widget/ext#Special" not in base.classes


def test_unmatched_assets_land_in_shared_bucket(tmp_path):
    settings = _settings(tmp_path)
    # A shape targeting a class under no declared ontology namespace.
    orphan = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix x: <https://other.example/thing#> .
x:ThingShape a sh:NodeShape ; sh:targetClass x:Thing .
"""
    (settings.shapes_dir / "orphan_shapes.ttl").write_text(orphan, encoding="utf-8")
    models = list_domain_models(settings)
    shared = next(m for m in models if m.is_shared)
    assert any(s.iri == "https://other.example/thing#ThingShape" for s in shared.shapes)
