"""Domain model assembly and drop-in domain import.

A *domain model* groups the three split assets a knowledge architect supplies —
an ontology (``owl:Ontology``), SHACL shapes, and R2RML mappings — back into a
single view, even though they live in separate configured directories. Grouping
is by namespace: a class, property, shape target, or mapping output whose IRI
falls under a domain's ontology namespace belongs to that domain. Assets that
match no declared ontology land in a synthetic "Shared / Core" bucket so nothing
is silently dropped.

The module also implements :func:`import_domain_files`, the write path behind the
browser upload: it validates every supplied file (RDF syntax, plus R2RML
governance metadata for mappings) and only writes — all files or none — once the
whole bundle is valid.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.mappings import MappingRecord, discover_mapping_files, list_mappings
from semantic_platform.ontology_version import ontology_metadata
from semantic_platform.r2rdf import MAP, RR, load_r2rml_mapping, validate_mapping
from semantic_platform.shapes import ShapeRecord, list_shapes

SHARED_LABEL = "Shared / Core"
ONTOLOGY_SUFFIX = ".ttl"
SHAPE_SUFFIX = ".ttl"
MAPPING_SUFFIXES = (".ttl", ".r2rml")


@dataclass(frozen=True)
class DomainModel:
    """A domain grouped from its ontology, shapes, and mappings."""

    ontology_iri: str
    label: str
    namespace: str
    version: str
    class_count: int
    property_count: int
    classes: tuple[str, ...]
    properties: tuple[str, ...]
    shapes: tuple[ShapeRecord, ...]
    mappings: tuple[MappingRecord, ...]
    is_shared: bool


@dataclass(frozen=True)
class ImportedFile:
    """One file written by an import."""

    kind: str
    filename: str
    target_path: str
    written: bool


@dataclass(frozen=True)
class ImportResult:
    """Outcome of importing a domain bundle."""

    ok: bool
    files: tuple[ImportedFile, ...]
    errors: tuple[str, ...]


def _base(iri: str) -> str:
    """Return the namespace base for an ontology IRI (trailing ``#``/``/`` stripped)."""
    return iri.rstrip("#/")


def _belongs(term: str, base: str) -> bool:
    """Return whether ``term`` falls under namespace ``base``."""
    return term == base or term.startswith(base + "#") or term.startswith(base + "/")


def _assign(term: str, bases: list[tuple[str, str]]) -> str | None:
    """Return the ontology IRI owning ``term``, preferring the most specific (longest) base."""
    best: tuple[str, str] | None = None
    for iri, base in bases:
        if _belongs(term, base) and (best is None or len(base) > len(best[1])):
            best = (iri, base)
    return best[0] if best else None


def _label(graph: Graph, node: URIRef, fallback: str) -> str:
    label = graph.value(node, RDFS.label)
    if label is not None:
        return str(label)
    local = fallback.rstrip("#/").rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    return local or fallback


def _mapping_terms(settings: Settings) -> dict[str, set[str]]:
    """Map each mapping IRI to the set of class and predicate IRIs it produces."""
    terms: dict[str, set[str]] = {}
    for path in discover_mapping_files(settings):
        graph = load_r2rml_mapping(path)
        for triples_map in set(graph.subjects(RDF.type, RR.TriplesMap)) | set(
            graph.subjects(RDF.type, MAP.Mapping)
        ):
            collected: set[str] = set()
            for subject_map in graph.objects(triples_map, RR.subjectMap):
                collected.update(str(c) for c in graph.objects(subject_map, RR["class"]))
            for pom in graph.objects(triples_map, RR.predicateObjectMap):
                collected.update(str(p) for p in graph.objects(pom, RR.predicate))
            terms[str(triples_map)] = collected
    return terms


def list_domain_models(settings: Settings | None = None) -> list[DomainModel]:
    """Group ontology classes/properties, shapes, and mappings into domain models."""
    settings = settings or load_settings()
    graph = load_graph(settings=settings)
    ontologies = ontology_metadata(settings=settings, graph=graph)
    bases = [(record.ontology, _base(record.ontology)) for record in ontologies]
    versions = {record.ontology: record.version for record in ontologies}

    classes = sorted(
        {str(c) for c in graph.subjects(RDF.type, OWL.Class)}
        | {str(c) for c in graph.subjects(RDF.type, RDFS.Class)}
    )
    properties = sorted(
        {str(p) for p in graph.subjects(RDF.type, OWL.ObjectProperty)}
        | {str(p) for p in graph.subjects(RDF.type, OWL.DatatypeProperty)}
        | {str(p) for p in graph.subjects(RDF.type, RDF.Property)}
    )
    shapes = list_shapes(settings)
    mappings = list_mappings(settings)
    mapping_terms = _mapping_terms(settings)

    buckets: dict[str | None, dict[str, list]] = {}

    def bucket(key: str | None) -> dict[str, list]:
        return buckets.setdefault(key, {"classes": [], "properties": [], "shapes": [], "mappings": []})

    for cls in classes:
        bucket(_assign(cls, bases))["classes"].append(cls)
    for prop in properties:
        bucket(_assign(prop, bases))["properties"].append(prop)
    for shape in shapes:
        owner = _assign(shape.target_class, bases) if shape.target_class else None
        bucket(owner)["shapes"].append(shape)
    for mapping in mappings:
        owner: str | None = None
        for term in sorted(mapping_terms.get(mapping.iri, set())):
            owner = _assign(term, bases)
            if owner is not None:
                break
        bucket(owner)["mappings"].append(mapping)

    models: list[DomainModel] = []
    for iri, base in sorted(bases, key=lambda pair: pair[0]):
        data = buckets.get(iri, {"classes": [], "properties": [], "shapes": [], "mappings": []})
        models.append(
            DomainModel(
                ontology_iri=iri,
                label=_label(graph, URIRef(iri), iri),
                namespace=base,
                version=versions.get(iri, ""),
                class_count=len(data["classes"]),
                property_count=len(data["properties"]),
                classes=tuple(data["classes"]),
                properties=tuple(data["properties"]),
                shapes=tuple(data["shapes"]),
                mappings=tuple(data["mappings"]),
                is_shared=False,
            )
        )

    shared = buckets.get(None)
    if shared and any(shared.values()):
        models.append(
            DomainModel(
                ontology_iri="",
                label=SHARED_LABEL,
                namespace="",
                version="",
                class_count=len(shared["classes"]),
                property_count=len(shared["properties"]),
                classes=tuple(shared["classes"]),
                properties=tuple(shared["properties"]),
                shapes=tuple(shared["shapes"]),
                mappings=tuple(shared["mappings"]),
                is_shared=True,
            )
        )
    return models


def _sanitize(filename: str) -> str:
    """Reduce an uploaded filename to a safe, directory-free name."""
    name = Path(filename.replace("\x00", "")).name
    allowed = "".join(ch for ch in name if ch.isalnum() or ch in "._-")
    return allowed


def _decode(content: bytes | str) -> str:
    return content.decode("utf-8") if isinstance(content, bytes) else content


def _validate_file(
    kind: str,
    spec: tuple[str, bytes | str],
    target_dir: Path,
    suffixes: tuple[str, ...],
    *,
    is_mapping: bool,
) -> tuple[str | None, str, list[str]]:
    """Validate one uploaded file; return (sanitized_name, text, errors)."""
    filename, content = spec
    errors: list[str] = []
    name = _sanitize(filename)
    if not name:
        errors.append(f"{kind}: invalid or empty filename '{filename}'.")
        return None, "", errors
    if Path(name).suffix.lower() not in suffixes:
        errors.append(f"{kind} ({name}): expected {' or '.join(suffixes)} file.")
        return name, "", errors
    resolved = (target_dir / name).resolve()
    if resolved.parent != target_dir.resolve():
        errors.append(f"{kind} ({name}): resolved path escapes the target directory.")
        return name, "", errors
    text = _decode(content)
    graph = Graph()
    try:
        graph.parse(data=text, format="turtle")
    except Exception as exc:  # noqa: BLE001 - surface any rdflib parse failure to the user
        errors.append(f"{kind} ({name}): invalid Turtle syntax: {exc}")
        return name, text, errors
    if is_mapping:
        result = validate_mapping(graph)
        errors.extend(f"{kind} ({name}): {error}" for error in result.errors)
    return name, text, errors


def import_domain_files(
    *,
    ontology: tuple[str, bytes | str] | None = None,
    shape: tuple[str, bytes | str] | None = None,
    mapping: tuple[str, bytes | str] | None = None,
    settings: Settings | None = None,
) -> ImportResult:
    """Validate and write a dropped-in domain bundle (ontology, shape, mapping).

    All supplied files are validated first; nothing is written unless the whole
    bundle is valid, so a failed import never leaves a partial set on disk.
    """
    settings = settings or load_settings()
    plans = [
        ("ontology", ontology, settings.ontology_dir, (ONTOLOGY_SUFFIX,), False),
        ("shape", shape, settings.shapes_dir, (SHAPE_SUFFIX,), False),
        ("mapping", mapping, settings.r2rml_dir, MAPPING_SUFFIXES, True),
    ]
    provided = [(kind, spec, target, suffixes, is_map) for kind, spec, target, suffixes, is_map in plans if spec]
    if not provided:
        return ImportResult(ok=False, files=(), errors=("No files provided.",))

    errors: list[str] = []
    writes: list[tuple[str, str, Path, str]] = []
    for kind, spec, target_dir, suffixes, is_mapping in provided:
        name, text, file_errors = _validate_file(kind, spec, target_dir, suffixes, is_mapping=is_mapping)
        errors.extend(file_errors)
        if not file_errors and name is not None:
            writes.append((kind, name, target_dir, text))

    if errors:
        return ImportResult(ok=False, files=(), errors=tuple(errors))

    written: list[ImportedFile] = []
    for kind, name, target_dir, text in writes:
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / name
        path.write_text(text, encoding="utf-8")
        written.append(ImportedFile(kind=kind, filename=name, target_path=str(path), written=True))
    return ImportResult(ok=True, files=tuple(written), errors=())
