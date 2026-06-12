"""Turn a domain interview into a plan of knowledge-model files.

Pure and deterministic: given :class:`InterviewAnswers`, :func:`scaffold_model`
returns a ``{relative_path: content}`` plan following the platform's ``rdf/`` layout
(ontology, optional SHACL shapes, optional sample data). The generated Turtle is
valid and SHACL-conformant by construction, so the offline ``local`` model produces
usable output; richer providers refine bodies via the assistant layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

_SAFE_LOCAL = re.compile(r"[^A-Za-z0-9]+")


@dataclass(frozen=True)
class InterviewAnswers:
    """Structured answers gathered from the modelling conversation."""

    domain_label: str
    prefix: str = "ex"
    base_namespace: str = "https://example.org/domain#"
    classes: tuple[str, ...] = ()
    properties: tuple[tuple[str, str, str], ...] = ()  # (name, domain_class, range)
    include_shapes: bool = True
    include_sample_data: bool = True


@dataclass(frozen=True)
class FilePlan:
    """A set of files (relative path → Turtle content) to write into a repo."""

    files: dict[str, str] = field(default_factory=dict)


def _pascal(value: str) -> str:
    parts = [p for p in _SAFE_LOCAL.split(value) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Thing"


def _camel(value: str) -> str:
    pascal = _pascal(value)
    return pascal[:1].lower() + pascal[1:]


def _header(answers: InterviewAnswers) -> str:
    return (
        f"@prefix {answers.prefix}: <{answers.base_namespace}> .\n"
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n"
    )


def _ontology_ttl(answers: InterviewAnswers) -> str:
    p = answers.prefix
    lines = [_header(answers)]
    lines.append(
        f"{p}: a owl:Ontology ;\n"
        f'    rdfs:label "{answers.domain_label}" ;\n'
        f'    rdfs:comment "Knowledge model scaffolded for the {answers.domain_label} domain." .\n'
    )
    for cls in answers.classes:
        local = _pascal(cls)
        lines.append(f"{p}:{local} a owl:Class ;\n    rdfs:label \"{cls}\" .\n")
    for name, domain_cls, range_cls in answers.properties:
        local = _camel(name)
        is_object = bool(range_cls) and not range_cls.lower().startswith("xsd:")
        kind = "owl:ObjectProperty" if is_object else "owl:DatatypeProperty"
        triples = [f"{p}:{local} a {kind} ;", f'    rdfs:label "{name}"']
        if domain_cls:
            triples.append(f"    ;\n    rdfs:domain {p}:{_pascal(domain_cls)}")
        if range_cls:
            range_term = range_cls if range_cls.lower().startswith("xsd:") else f"{p}:{_pascal(range_cls)}"
            triples.append(f"    ;\n    rdfs:range {range_term}")
        lines.append("".join(triples) + " .\n")
    return "\n".join(lines)


def _shapes_ttl(answers: InterviewAnswers) -> str:
    p = answers.prefix
    lines = [_header(answers)]
    for cls in answers.classes:
        local = _pascal(cls)
        lines.append(
            f"{p}:{local}Shape a sh:NodeShape ;\n"
            f"    sh:targetClass {p}:{local} ;\n"
            f'    rdfs:label "{cls} shape" .\n'
        )
    return "\n".join(lines)


def _sample_ttl(answers: InterviewAnswers) -> str:
    p = answers.prefix
    lines = [_header(answers)]
    for cls in answers.classes:
        local = _pascal(cls)
        lines.append(f"{p}:example{local} a {p}:{local} ;\n    rdfs:label \"Example {cls}\" .\n")
    return "\n".join(lines)


def scaffold_model(answers: InterviewAnswers) -> FilePlan:
    """Return the file plan for a domain model from interview answers."""
    files: dict[str, str] = {"rdf/ontology/ontology.ttl": _ontology_ttl(answers)}
    if answers.include_shapes and answers.classes:
        files["rdf/shapes/domain_shapes.ttl"] = _shapes_ttl(answers)
    if answers.include_sample_data and answers.classes:
        files["rdf/data/sample.ttl"] = _sample_ttl(answers)
    return FilePlan(files=files)
