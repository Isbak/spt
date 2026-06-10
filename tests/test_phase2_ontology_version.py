import pytest

from semantic_platform.ontology_version import (
    compare_ontology_versions,
    extract_ontology_version,
    ontology_version_summary,
    validate_version_format,
)


def test_ontology_version_extraction():
    assert extract_ontology_version("https://example.org/semantic-platform/core") == "0.2.0"


def test_ontology_version_validation_and_comparison():
    assert validate_version_format("0.2.0")
    assert not validate_version_format("v0.2")
    assert compare_ontology_versions("0.2.0", "0.1.9") == 1
    with pytest.raises(ValueError):
        compare_ontology_versions("bad", "0.1.0")
    assert ontology_version_summary()["invalid_versions"] == []
