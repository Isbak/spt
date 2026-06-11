"""Environment-driven configuration for the Semantic Platform."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    project_root: Path
    rdf_root: Path
    ontology_dir: Path
    vocabularies_dir: Path
    data_dir: Path
    shapes_dir: Path
    queries_dir: Path
    graphs_dir: Path
    r2rml_dir: Path
    sql_dir: Path
    output_dir: Path
    source_database_url: str | None
    source_sql_files: tuple[Path, ...]
    llm_provider: str
    llm_model: str | None
    fuseki_base_url: str
    fuseki_dataset: str
    fuseki_username: str | None
    fuseki_password: str | None
    flask_host: str
    flask_port: int
    default_query_file: Path

    @property
    def fuseki_dataset_url(self) -> str:
        """Return the configured Fuseki dataset URL."""
        return f"{self.fuseki_base_url.rstrip('/')}/{self.fuseki_dataset.strip('/')}"

    @property
    def fuseki_query_url(self) -> str:
        """Return the SPARQL query endpoint URL."""
        return f"{self.fuseki_dataset_url}/query"

    @property
    def fuseki_update_url(self) -> str:
        """Return the SPARQL update endpoint URL."""
        return f"{self.fuseki_dataset_url}/update"

    @property
    def fuseki_data_url(self) -> str:
        """Return the Graph Store Protocol endpoint URL."""
        return f"{self.fuseki_dataset_url}/data"


def _root_from_env() -> Path:
    configured = os.getenv("SEMANTIC_PLATFORM_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def load_settings() -> Settings:
    """Load settings from environment variables with repository-local defaults."""
    root = _root_from_env()
    rdf_root = Path(os.getenv("RDF_ROOT", root / "rdf")).expanduser().resolve()
    queries_dir = Path(os.getenv("RDF_QUERIES_DIR", rdf_root / "queries")).expanduser().resolve()
    default_query = Path(
        os.getenv("DEFAULT_SPARQL_QUERY", queries_dir / "validation-summary.rq")
    ).expanduser().resolve()
    sql_dir = Path(os.getenv("MAPPINGS_SQL_DIR", root / "mappings" / "sql")).expanduser().resolve()
    configured_sql = os.getenv("MATERIALIZE_SQL_FILES", "")
    source_sql_files = tuple(
        Path(item.strip()).expanduser().resolve()
        for item in configured_sql.replace(":", ",").split(",")
        if item.strip()
    )

    return Settings(
        project_root=root,
        rdf_root=rdf_root,
        ontology_dir=Path(os.getenv("RDF_ONTOLOGY_DIR", rdf_root / "ontology")).expanduser().resolve(),
        vocabularies_dir=Path(
            os.getenv("RDF_VOCABULARIES_DIR", rdf_root / "vocabularies")
        ).expanduser().resolve(),
        data_dir=Path(os.getenv("RDF_DATA_DIR", rdf_root / "data")).expanduser().resolve(),
        shapes_dir=Path(os.getenv("RDF_SHAPES_DIR", rdf_root / "shapes")).expanduser().resolve(),
        queries_dir=queries_dir,
        graphs_dir=Path(os.getenv("RDF_GRAPHS_DIR", rdf_root / "graphs")).expanduser().resolve(),
        r2rml_dir=Path(os.getenv("MAPPINGS_R2RML_DIR", root / "mappings" / "r2rml")).expanduser().resolve(),
        sql_dir=sql_dir,
        output_dir=Path(os.getenv("OUTPUT_DIR", root / "output")).expanduser().resolve(),
        source_database_url=os.getenv("SOURCE_DATABASE_URL") or None,
        source_sql_files=source_sql_files,
        llm_provider=(os.getenv("LLM_PROVIDER") or "local").strip().lower(),
        llm_model=os.getenv("LLM_MODEL") or None,
        fuseki_base_url=os.getenv("FUSEKI_BASE_URL", "http://localhost:3030"),
        fuseki_dataset=os.getenv("FUSEKI_DATASET", "semantic-platform"),
        fuseki_username=os.getenv("FUSEKI_USERNAME") or None,
        fuseki_password=os.getenv("FUSEKI_PASSWORD") or os.getenv("FUSEKI_ADMIN_PASSWORD") or None,
        flask_host=os.getenv("FLASK_HOST", "0.0.0.0"),
        flask_port=int(os.getenv("FLASK_PORT", "5000")),
        default_query_file=default_query,
    )
