"""Tests for SHACL shape discovery."""

from __future__ import annotations

import dataclasses

from semantic_platform.config import load_settings
from semantic_platform.shapes import list_shapes


def test_list_shapes_returns_repository_shapes():
    shapes = list_shapes()
    assert shapes, "expected repository SHACL shapes to be discovered"
    node_shapes = [s for s in shapes if s.kind == "NodeShape"]
    assert node_shapes
    # At least one node shape targets a class and declares property constraints.
    assert any(s.target_class for s in node_shapes)
    assert any(s.path_count > 0 for s in node_shapes)
    # Every record carries its source filename.
    assert all(s.file.endswith((".ttl", ".rdf", ".xml", ".nt", ".n3")) for s in shapes)


def test_list_shapes_missing_directory(tmp_path):
    settings = dataclasses.replace(load_settings(), shapes_dir=tmp_path / "absent")
    assert list_shapes(settings) == []
