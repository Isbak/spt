"""SHACL shape discovery services.

Surfaces the SHACL shapes living in ``settings.shapes_dir`` as structured
records for the Shapes UI page and for grouping shapes into domain models. Each
shape file is parsed individually so the originating filename is preserved.
"""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SH

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import RDF_EXTENSIONS


@dataclass(frozen=True)
class ShapeRecord:
    """Catalog record for one SHACL shape."""

    iri: str
    label: str
    target_class: str
    path_count: int
    file: str
    kind: str


def _label(graph: Graph, node: URIRef) -> str:
    label = graph.value(node, RDFS.label)
    if label is not None:
        return str(label)
    text = str(node)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or text


def list_shapes(settings: Settings | None = None) -> list[ShapeRecord]:
    """List SHACL node and property shapes with target class and constraint counts."""
    settings = settings or load_settings()
    records: list[ShapeRecord] = []
    shapes_dir = settings.shapes_dir
    if not shapes_dir.is_dir():
        return records
    files = sorted(p for p in shapes_dir.rglob("*") if p.suffix.lower() in RDF_EXTENSIONS)
    for path in files:
        graph = Graph()
        graph.parse(path, format=RDF_EXTENSIONS[path.suffix.lower()])
        for kind, shape_type in (("NodeShape", SH.NodeShape), ("PropertyShape", SH.PropertyShape)):
            for shape in sorted(set(graph.subjects(RDF.type, shape_type)), key=str):
                target = graph.value(shape, SH.targetClass)
                records.append(
                    ShapeRecord(
                        iri=str(shape),
                        label=_label(graph, shape),
                        target_class=str(target) if target is not None else "",
                        path_count=len(list(graph.objects(shape, SH.property))),
                        file=path.name,
                        kind=kind,
                    )
                )
    return records
