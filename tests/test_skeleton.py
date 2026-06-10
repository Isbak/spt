"""Skeleton smoke tests."""

import importlib


MODULES = [
    "semantic_platform.api",
    "semantic_platform.config",
    "semantic_platform.fuseki",
    "semantic_platform.governance",
    "semantic_platform.graph",
    "semantic_platform.provenance",
    "semantic_platform.query",
    "semantic_platform.r2rdf",
    "semantic_platform.reasoning",
    "semantic_platform.validate",
]


def test_semantic_platform_modules_are_importable():
    """The package skeleton exposes the expected module placeholders."""
    for module in MODULES:
        assert importlib.import_module(module)
