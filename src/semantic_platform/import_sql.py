"""SQL-to-RDF import workflow with mapping provenance."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF

from semantic_platform.r2rdf import MAP, SP, create_execution_provenance

DEFAULT_SOURCE_DATASET = URIRef("https://example.org/source-dataset/datasets")
DEFAULT_MAPPING = URIRef("https://example.org/mapping/dataset-r2rml")
DEFAULT_TARGET_GRAPH = URIRef("urn:graph:integration")


def load_sqlite_database(schema_sql: Path | str, sample_data_sql: Path | str) -> sqlite3.Connection:
    """Create an in-memory SQLite database from schema and sample data SQL files."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(Path(schema_sql).read_text(encoding="utf-8"))
    connection.executescript(Path(sample_data_sql).read_text(encoding="utf-8"))
    return connection


def query_rows(connection: sqlite3.Connection, query: str) -> list[dict[str, str]]:
    """Execute a SQL query and return row dictionaries."""
    return [dict(row) for row in connection.execute(query).fetchall()]


def sql_rows_to_rdf(rows: list[dict[str, str]], *, table: str, source_dataset: URIRef = DEFAULT_SOURCE_DATASET) -> Graph:
    """Convert SQL result rows from supported sample tables to RDF."""
    graph = Graph()
    graph.bind("sp", SP)
    graph.bind("map", MAP)
    for row in rows:
        if table == "dataset":
            subject = URIRef(f"https://example.org/resource/dataset/{row['dataset_id']}")
            graph.add((subject, RDF.type, SP.Dataset))
            graph.add((subject, SP.identifier, Literal(row["dataset_id"])))
            graph.add((subject, DCTERMS.title, Literal(row["dataset_name"])))
            graph.add((subject, URIRef("http://www.w3.org/2002/07/owl#versionInfo"), Literal(row["version"])))
        elif table == "organization":
            subject = URIRef(f"https://example.org/resource/organization/{row['organization_id']}")
            graph.add((subject, RDF.type, SP.Entity))
            graph.add((subject, SP.identifier, Literal(row["organization_id"])))
            graph.add((subject, SP.name, Literal(row["organization_name"])))
        elif table == "source_system":
            subject = URIRef(f"https://example.org/source-system/{row['source_system_id']}")
            graph.add((subject, RDF.type, MAP.SourceSystem))
            graph.add((subject, SP.identifier, Literal(row["source_system_id"])))
            graph.add((subject, SP.name, Literal(row["source_system_name"])))
        else:
            subject = URIRef(f"https://example.org/resource/person/{row['person_id']}")
            graph.add((subject, RDF.type, SP.Entity))
            graph.add((subject, SP.identifier, Literal(row["person_id"])))
            graph.add((subject, SP.name, Literal(f"{row['given_name']} {row['family_name']}")))
        graph.add((subject, SP.belongsToDataset, source_dataset))
    return graph


def import_sql_source(
    schema_sql: Path | str,
    sample_data_sql: Path | str,
    *,
    table: str = "dataset",
    mapping_iri: URIRef = DEFAULT_MAPPING,
    source_dataset: URIRef = DEFAULT_SOURCE_DATASET,
    target_graph: URIRef = DEFAULT_TARGET_GRAPH,
) -> Graph:
    """Read SQL source data, convert to RDF, and add execution provenance."""
    connection = load_sqlite_database(schema_sql, sample_data_sql)
    try:
        rows = query_rows(connection, f"SELECT * FROM {table}")
    finally:
        connection.close()
    graph = sql_rows_to_rdf(rows, table=table, source_dataset=source_dataset)
    graph += create_execution_provenance(
        mapping_iri=mapping_iri,
        source_dataset=source_dataset,
        target_graph=target_graph,
        record_count=len(rows),
    )
    return graph


def main() -> None:
    """CLI entry point for local SQL import smoke tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Import sample SQL data as RDF/Turtle.")
    parser.add_argument("schema_sql", nargs="?", default="mappings/sql/schema.sql")
    parser.add_argument("sample_data_sql", nargs="?", default="mappings/sql/sample_data.sql")
    parser.add_argument("--table", default="dataset")
    args = parser.parse_args()
    graph = import_sql_source(args.schema_sql, args.sample_data_sql, table=args.table)
    print(graph.serialize(format="turtle"))


if __name__ == "__main__":
    main()
