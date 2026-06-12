"""Environment-driven configuration for the Semantic Platform."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import logging
import os

LOGGER = logging.getLogger(__name__)

#: File under ``workspace_root`` holding UI-persisted settings (e.g. model choice).
PLATFORM_CONFIG_FILENAME = "platform_config.json"


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
    workspace_root: Path
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


def _persisted_settings(workspace_root: Path) -> dict[str, str]:
    """Return UI-persisted settings from the workspace config file (empty if absent).

    These act as a layer **below** environment variables, so a choice made in the
    setup UI survives a restart without editing ``.env`` while env still wins.
    """
    config_file = workspace_root / PLATFORM_CONFIG_FILENAME
    if not config_file.is_file():
        return {}
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - corrupt/unreadable file
        LOGGER.warning("Ignoring unreadable workspace config: %s", config_file)
        return {}
    return data if isinstance(data, dict) else {}


def load_settings() -> Settings:
    """Load settings from environment variables with repository-local defaults."""
    root = _root_from_env()
    workspace_root = Path(os.getenv("WORKSPACE_ROOT", root / "workspace")).expanduser().resolve()
    persisted = _persisted_settings(workspace_root)
    llm_provider = (
        os.getenv("LLM_PROVIDER") or persisted.get("llm_provider") or "local"
    ).strip().lower()
    llm_model = os.getenv("LLM_MODEL") or persisted.get("llm_model") or None
    rdf_root = Path(os.getenv("RDF_ROOT", root / "rdf")).expanduser().resolve()
    queries_dir = Path(os.getenv("RDF_QUERIES_DIR", rdf_root / "queries")).expanduser().resolve()
    default_query = Path(
        os.getenv("DEFAULT_SPARQL_QUERY", queries_dir / "validation-summary.rq")
    ).expanduser().resolve()
    sql_dir = Path(os.getenv("MAPPINGS_SQL_DIR", root / "mappings" / "sql")).expanduser().resolve()
    # Fuseki credentials. The HTTP client only authenticates when BOTH username and
    # password are present, so default the username to "admin" (the Fuseki admin
    # user) when only a password / FUSEKI_ADMIN_PASSWORD is supplied. Otherwise a
    # lone FUSEKI_ADMIN_PASSWORD would silently send no auth and 401 on writes.
    fuseki_password = os.getenv("FUSEKI_PASSWORD") or os.getenv("FUSEKI_ADMIN_PASSWORD") or None
    fuseki_username = os.getenv("FUSEKI_USERNAME") or ("admin" if fuseki_password else None)
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
        workspace_root=workspace_root,
        source_database_url=os.getenv("SOURCE_DATABASE_URL") or None,
        source_sql_files=source_sql_files,
        llm_provider=llm_provider,
        llm_model=llm_model,
        fuseki_base_url=os.getenv("FUSEKI_BASE_URL", "http://localhost:3030"),
        fuseki_dataset=os.getenv("FUSEKI_DATASET", "semantic-platform"),
        fuseki_username=fuseki_username,
        fuseki_password=fuseki_password,
        flask_host=os.getenv("FLASK_HOST", "0.0.0.0"),
        flask_port=int(os.getenv("FLASK_PORT", "5000")),
        default_query_file=default_query,
    )
