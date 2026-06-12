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

#: Storage roles. Each role is an independently placeable (local or remote) store.
#: ``system`` is the platform's own self-model and stays local/file-authored;
#: ``agents`` holds agent registry/memory/observations + PROV-O lineage; ``business``
#: holds domain instance data. See ADR-0017.
DATASET_ROLES = ("system", "agents", "business")

#: Default Fuseki dataset name per role. ``system`` keeps the legacy name so existing
#: single-dataset deployments are unaffected.
DEFAULT_DATASET_NAMES = {
    "system": "semantic-platform",
    "agents": "semantic-platform-agents",
    "business": "semantic-platform-business",
}


@dataclass(frozen=True)
class FusekiDataset:
    """Endpoint bundle for a single Fuseki dataset (one storage role).

    Each role (``system``/``agents``/``business``) is served by its own dataset, which
    may live on a different Fuseki server, so any role can be placed locally or remotely
    independently of the others.
    """

    base_url: str
    dataset: str
    username: str | None
    password: str | None

    @property
    def dataset_url(self) -> str:
        """Return the configured Fuseki dataset URL."""
        return f"{self.base_url.rstrip('/')}/{self.dataset.strip('/')}"

    @property
    def query_url(self) -> str:
        """Return the SPARQL query endpoint URL."""
        return f"{self.dataset_url}/query"

    @property
    def update_url(self) -> str:
        """Return the SPARQL update endpoint URL."""
        return f"{self.dataset_url}/update"

    @property
    def data_url(self) -> str:
        """Return the Graph Store Protocol endpoint URL."""
        return f"{self.dataset_url}/data"


@dataclass(frozen=True)
class SourceDatabase:
    """Relational source bundle for a storage role (read side).

    Mirrors :class:`FusekiDataset` on the ingest side: a role's warehouse can be a
    self-contained in-memory SQLite database (built from ``sql_files``/``sql_dir``) or an
    external warehouse (``database_url``), placed locally or remotely. ``system`` has no
    source bundle (it is authored from ``rdf/`` files). See ADR-0017.
    """

    database_url: str | None
    sql_files: tuple[Path, ...]
    sql_dir: Path


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
    output_dir: Path
    workspace_root: Path
    llm_provider: str
    llm_model: str | None
    # Per-role storage bundles (ADR-0017). Each may be placed locally or remotely.
    fuseki_system: FusekiDataset
    fuseki_agents: FusekiDataset
    fuseki_business: FusekiDataset
    source_business: SourceDatabase
    source_agents: SourceDatabase
    flask_host: str
    flask_port: int
    default_query_file: Path

    def fuseki(self, role: str = "system") -> FusekiDataset:
        """Return the Fuseki bundle for a storage role (defaults to ``system``)."""
        try:
            return getattr(self, f"fuseki_{role}")
        except AttributeError as exc:  # pragma: no cover - guards programmer error
            raise ValueError(f"Unknown Fuseki role: {role!r}") from exc

    def source(self, role: str = "business") -> SourceDatabase:
        """Return the relational source bundle for a storage role.

        Only ``business`` and ``agents`` have sources; ``system`` is file-authored.
        """
        try:
            return getattr(self, f"source_{role}")
        except AttributeError as exc:
            raise ValueError(f"No relational source for role: {role!r}") from exc

    # --- Backward-compatibility aliases (delegate to the system / business bundles) ---
    # Existing callers and single-store deployments use the flat ``fuseki_*`` / ``source_*``
    # names; keep them working by delegating to the default role bundles.

    @property
    def fuseki_base_url(self) -> str:
        return self.fuseki_system.base_url

    @property
    def fuseki_dataset(self) -> str:
        return self.fuseki_system.dataset

    @property
    def fuseki_username(self) -> str | None:
        return self.fuseki_system.username

    @property
    def fuseki_password(self) -> str | None:
        return self.fuseki_system.password

    @property
    def fuseki_dataset_url(self) -> str:
        """Return the configured Fuseki dataset URL."""
        return self.fuseki_system.dataset_url

    @property
    def fuseki_query_url(self) -> str:
        """Return the SPARQL query endpoint URL."""
        return self.fuseki_system.query_url

    @property
    def fuseki_update_url(self) -> str:
        """Return the SPARQL update endpoint URL."""
        return self.fuseki_system.update_url

    @property
    def fuseki_data_url(self) -> str:
        """Return the Graph Store Protocol endpoint URL."""
        return self.fuseki_system.data_url

    @property
    def source_database_url(self) -> str | None:
        return self.source_business.database_url

    @property
    def source_sql_files(self) -> tuple[Path, ...]:
        return self.source_business.sql_files

    @property
    def sql_dir(self) -> Path:
        return self.source_business.sql_dir


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
    default_sql_dir = Path(
        os.getenv("MAPPINGS_SQL_DIR", root / "mappings" / "sql")
    ).expanduser().resolve()

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
        output_dir=Path(os.getenv("OUTPUT_DIR", root / "output")).expanduser().resolve(),
        workspace_root=workspace_root,
        llm_provider=llm_provider,
        llm_model=llm_model,
        fuseki_system=_fuseki_bundle("system"),
        fuseki_agents=_fuseki_bundle("agents"),
        fuseki_business=_fuseki_bundle("business"),
        source_business=_source_bundle("business", default_sql_dir),
        source_agents=_source_bundle("agents", default_sql_dir),
        flask_host=os.getenv("FLASK_HOST", "0.0.0.0"),
        flask_port=int(os.getenv("FLASK_PORT", "5000")),
        default_query_file=default_query,
    )


def _parse_sql_files(value: str) -> tuple[Path, ...]:
    """Parse a comma/colon-separated list of SQL file paths."""
    return tuple(
        Path(item.strip()).expanduser().resolve()
        for item in value.replace(":", ",").split(",")
        if item.strip()
    )


def _fuseki_bundle(role: str) -> FusekiDataset:
    """Build a Fuseki bundle for ``role`` from env, falling back to the shared settings.

    Precedence per field: ``FUSEKI_{ROLE}_*`` → shared ``FUSEKI_*`` → role default. This
    keeps a single ``FUSEKI_BASE_URL`` (today's config) co-locating every role locally,
    while a role-specific base URL places that role's dataset on another server.
    """
    prefix = f"FUSEKI_{role.upper()}_"
    base_url = (
        os.getenv(f"{prefix}BASE_URL")
        or os.getenv("FUSEKI_BASE_URL")
        or "http://localhost:3030"
    )
    dataset = os.getenv(f"{prefix}DATASET") or (
        os.getenv("FUSEKI_DATASET", DEFAULT_DATASET_NAMES[role])
        if role == "system"
        else DEFAULT_DATASET_NAMES[role]
    )
    # Credentials. The HTTP client only authenticates when BOTH username and password are
    # present, so default the username to "admin" (the Fuseki admin user) when only a
    # password / FUSEKI_ADMIN_PASSWORD is supplied. Otherwise a lone password would
    # silently send no auth and 401 on writes.
    password = (
        os.getenv(f"{prefix}PASSWORD")
        or os.getenv("FUSEKI_PASSWORD")
        or os.getenv("FUSEKI_ADMIN_PASSWORD")
        or None
    )
    username = (
        os.getenv(f"{prefix}USERNAME")
        or os.getenv("FUSEKI_USERNAME")
        or ("admin" if password else None)
    )
    return FusekiDataset(base_url=base_url, dataset=dataset, username=username, password=password)


def _source_bundle(role: str, default_sql_dir: Path) -> SourceDatabase:
    """Build a relational source bundle for ``role`` from env, with legacy fallbacks.

    Precedence per field: ``SOURCE_{ROLE}_*`` / ``MATERIALIZE_{ROLE}_SQL_FILES`` /
    ``MAPPINGS_{ROLE}_SQL_DIR`` → shared ``SOURCE_DATABASE_URL`` / ``MATERIALIZE_SQL_FILES``
    / ``MAPPINGS_SQL_DIR``. So an existing single ``SOURCE_DATABASE_URL`` feeds every role.
    """
    prefix = role.upper()
    database_url = os.getenv(f"SOURCE_{prefix}_DATABASE_URL") or os.getenv("SOURCE_DATABASE_URL") or None
    sql_files = _parse_sql_files(
        os.getenv(f"MATERIALIZE_{prefix}_SQL_FILES") or os.getenv("MATERIALIZE_SQL_FILES", "")
    )
    sql_dir_env = os.getenv(f"MAPPINGS_{prefix}_SQL_DIR")
    sql_dir = Path(sql_dir_env).expanduser().resolve() if sql_dir_env else default_sql_dir
    return SourceDatabase(database_url=database_url, sql_files=sql_files, sql_dir=sql_dir)
