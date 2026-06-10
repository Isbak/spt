from pathlib import Path

from semantic_platform.validate import run_validation, validate_rdf_syntax


def test_validation_passes_for_repository_assets():
    syntax_results, shacl_report = run_validation()
    assert syntax_results
    assert all(result.valid for result in syntax_results)
    assert shacl_report.conforms
    assert "Conforms: True" in shacl_report.report_text


def test_rdf_syntax_validation_reports_invalid_file(tmp_path: Path):
    invalid = tmp_path / "invalid.ttl"
    invalid.write_text("@prefix ex: <https://example.org/> .\nex:s ex:p .", encoding="utf-8")
    results = validate_rdf_syntax([invalid])
    assert len(results) == 1
    assert not results[0].valid
