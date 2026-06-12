from pathlib import Path

from rdflib import Graph

from semantic_platform.validate import run_validation, validate_rdf_syntax, validate_shacl


def test_validation_passes_for_repository_assets():
    syntax_results, shacl_report = run_validation()
    assert syntax_results
    assert all(result.valid for result in syntax_results)
    assert shacl_report.conforms
    assert "Conforms: True" in shacl_report.report_text


def test_validate_shacl_with_explicit_shapes_graph():
    shapes = Graph().parse(
        data=(
            "@prefix sh: <http://www.w3.org/ns/shacl#> ."
            "@prefix ex: <https://example.org/#> ."
            "ex:PersonShape a sh:NodeShape ; sh:targetClass ex:Person ;"
            "  sh:property [ sh:path ex:name ; sh:minCount 1 ] ."
        ),
        format="turtle",
    )
    conforming = Graph().parse(
        data="@prefix ex: <https://example.org/#> . ex:p a ex:Person ; ex:name \"A\" .",
        format="turtle",
    )
    violating = Graph().parse(
        data="@prefix ex: <https://example.org/#> . ex:p a ex:Person .",
        format="turtle",
    )
    assert validate_shacl(data_graph=conforming, shapes_graph=shapes).conforms is True
    assert validate_shacl(data_graph=violating, shapes_graph=shapes).conforms is False


def test_rdf_syntax_validation_reports_invalid_file(tmp_path: Path):
    invalid = tmp_path / "invalid.ttl"
    invalid.write_text("@prefix ex: <https://example.org/> .\nex:s ex:p .", encoding="utf-8")
    results = validate_rdf_syntax([invalid])
    assert len(results) == 1
    assert not results[0].valid
