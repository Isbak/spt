"""CSV-to-RDF import workflow with mapping provenance."""

from __future__ import annotations

import csv
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF

from semantic_platform.r2rdf import MAP, SP, create_execution_provenance

DEFAULT_SOURCE_DATASET = URIRef("https://example.org/source-dataset/people")
DEFAULT_MAPPING = URIRef("https://example.org/mapping/person-r2rml")
DEFAULT_TARGET_GRAPH = URIRef("urn:graph:masterdata")


def read_csv(path: Path | str) -> list[dict[str, str]]:
    """Read a CSV file into row dictionaries."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def csv_rows_to_rdf(
    rows: list[dict[str, str]],
    *,
    entity_type: str = "person",
    source_dataset: URIRef = DEFAULT_SOURCE_DATASET,
) -> Graph:
    """Convert supported CSV rows to RDF resources."""
    graph = Graph()
    graph.bind("sp", SP)
    graph.bind("map", MAP)
    for row in rows:
        if entity_type == "dataset" or "dataset_name" in row:
            subject = URIRef(f"https://example.org/resource/dataset/{row['dataset_id']}")
            graph.add((subject, RDF.type, SP.Dataset))
            graph.add((subject, SP.identifier, Literal(row["dataset_id"])))
            graph.add((subject, DCTERMS.title, Literal(row["dataset_name"])))
            graph.add((subject, URIRef("http://www.w3.org/2002/07/owl#versionInfo"), Literal(row["version"])))
        elif entity_type == "organization" or "organization_name" in row:
            subject = URIRef(f"https://example.org/resource/organization/{row['organization_id']}")
            graph.add((subject, RDF.type, SP.Entity))
            graph.add((subject, SP.identifier, Literal(row["organization_id"])))
            graph.add((subject, SP.name, Literal(row["organization_name"])))
            graph.add((subject, SP.status, URIRef(f"https://example.org/status/{row['status_code']}")))
        else:
            subject = URIRef(f"https://example.org/resource/person/{row['person_id']}")
            graph.add((subject, RDF.type, SP.Entity))
            graph.add((subject, SP.identifier, Literal(row["person_id"])))
            graph.add((subject, SP.name, Literal(f"{row['given_name']} {row['family_name']}")))
            graph.add((subject, URIRef("https://example.org/semantic-platform/core#email"), Literal(row["email"])))
            if row.get("organization_id"):
                graph.add(
                    (
                        subject,
                        URIRef("https://example.org/semantic-platform/core#memberOf"),
                        URIRef(f"https://example.org/resource/organization/{row['organization_id']}"),
                    )
                )
        graph.add((subject, SP.belongsToDataset, source_dataset))
    return graph


def import_csv_file(
    path: Path | str,
    *,
    entity_type: str | None = None,
    mapping_iri: URIRef = DEFAULT_MAPPING,
    source_dataset: URIRef = DEFAULT_SOURCE_DATASET,
    target_graph: URIRef = DEFAULT_TARGET_GRAPH,
) -> Graph:
    """Read CSV, convert rows to RDF, and add execution provenance."""
    rows = read_csv(path)
    inferred_type = entity_type or _infer_entity_type(Path(path), rows)
    graph = csv_rows_to_rdf(rows, entity_type=inferred_type, source_dataset=source_dataset)
    graph += create_execution_provenance(
        mapping_iri=mapping_iri,
        source_dataset=source_dataset,
        target_graph=target_graph,
        record_count=len(rows),
    )
    return graph


def _infer_entity_type(path: Path, rows: list[dict[str, str]]) -> str:
    if "dataset" in path.stem or (rows and "dataset_name" in rows[0]):
        return "dataset"
    if "organization" in path.stem or (rows and "organization_name" in rows[0]):
        return "organization"
    return "person"


def main() -> None:
    """CLI entry point for local CSV import smoke tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Import a CSV file as RDF/Turtle.")
    parser.add_argument("csv_file", nargs="?", default="mappings/csv/people.csv")
    args = parser.parse_args()
    graph = import_csv_file(args.csv_file)
    print(graph.serialize(format="turtle"))


if __name__ == "__main__":
    main()
