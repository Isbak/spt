"""Application service facade used by Flask routes and scripts."""

from __future__ import annotations

import os
from typing import Any

from semantic_platform.advisory import (
    AdvisoryResult,
    Criterion,
    candidates_from_graph,
    recommend,
)
from semantic_platform.agents.assist import ExplanationResult, generate_explanation
from semantic_platform.agents.llm import (
    anthropic_configured,
    ollama_reachable,
    resolve_language_model,
)
from semantic_platform.authoring import workspace_config as wc
from semantic_platform.authoring.assistant import AuthoringResult, author_model, chat_turn, open_pr
from semantic_platform.authoring.gitrepo import GitRepo, PullRequestRef
from semantic_platform.authoring.scaffold import InterviewAnswers
from semantic_platform.config import Settings, load_settings
from semantic_platform.domain_models import (
    DomainModel,
    list_domain_models,
)
from semantic_platform.fuseki import FusekiClient, FusekiStatus
from semantic_platform.named_graphs import dataset_for_graph
from semantic_platform.graph import GraphStats, graph_stats, load_graph
from semantic_platform.materialize import (
    FusekiLoadResult,
    MaterializationResult,
    materialize_mappings,
    push_to_fuseki,
)
from semantic_platform.query import execute_query, read_query, result_rows
from semantic_platform.shapes import ShapeRecord, list_shapes
from semantic_platform.validate import ShaclValidationReport, SyntaxValidationResult, run_validation


def get_graph_stats(settings: Settings | None = None) -> GraphStats:
    """Load configured RDF assets and return basic statistics."""
    return graph_stats(load_graph(settings=settings or load_settings()))


def get_ontology_text(settings: Settings | None = None) -> str:
    """Return concatenated ontology Turtle for the simple UI."""
    settings = settings or load_settings()
    chunks = []
    for path in sorted(settings.ontology_dir.glob("*.ttl")):
        chunks.append(f"# {path.name}\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(chunks)


def get_domain_models(settings: Settings | None = None) -> list[DomainModel]:
    """Return domain models grouping ontology, shapes, and mappings by namespace."""
    return list_domain_models(settings=settings or load_settings())


def list_shape_records(settings: Settings | None = None) -> list[ShapeRecord]:
    """Return discovered SHACL shapes for the Shapes UI page."""
    return list_shapes(settings=settings or load_settings())


def run_local_query(query_text: str | None = None, settings: Settings | None = None) -> list[dict[str, Any]]:
    """Run a SPARQL query against local RDF assets."""
    settings = settings or load_settings()
    query_text = query_text or read_query(settings.default_query_file)
    return result_rows(execute_query(query_text, load_graph(settings=settings)))


def validate_platform(settings: Settings | None = None) -> tuple[list[SyntaxValidationResult], ShaclValidationReport]:
    """Run all local validation checks."""
    return run_validation(settings=settings or load_settings())


def fuseki_health(settings: Settings | None = None) -> FusekiStatus:
    """Return Fuseki health status."""
    return FusekiClient(settings=settings or load_settings()).health_check()


def upload_default_graphs(settings: Settings | None = None) -> None:
    """Upload ontology, vocabulary and data assets to their per-role named graphs."""
    settings = settings or load_settings()
    graph_map = {
        settings.ontology_dir / "core.ttl": "urn:semantic-platform:graph:ontology",
        settings.vocabularies_dir / "example-skos.ttl": "urn:semantic-platform:graph:reference",
        settings.data_dir / "example-data.ttl": "urn:semantic-platform:graph:data",
    }
    for path, graph_uri in graph_map.items():
        if path.exists():
            FusekiClient.for_graph(graph_uri, settings=settings).upload_graph(path, graph_uri)


def materialize_sources(settings: Settings | None = None) -> list[MaterializationResult]:
    """Materialize all R2RML mappings against the configured relational source."""
    return materialize_mappings(settings=settings or load_settings())


def load_sources_into_fuseki(settings: Settings | None = None) -> list[FusekiLoadResult]:
    """Materialize mappings and push the resulting graphs into Fuseki."""
    settings = settings or load_settings()
    return push_to_fuseki(materialize_mappings(settings=settings), settings=settings)


def explain_with_agent(
    agent_id: str, scope: str, question: str, settings: Settings | None = None
) -> ExplanationResult:
    """Governed read-only LLM assist: have an agent explain data it may read."""
    return generate_explanation(agent_id, scope, question, settings=settings or load_settings())


# --- LLM model configuration -------------------------------------------------


def get_model_config(settings: Settings | None = None) -> wc.ModelConfig:
    """Return the persisted LLM provider/model selection."""
    return wc.get_model_config(settings or load_settings())


def set_model_config(
    provider: str,
    model: str | None = None,
    ollama_base_url: str | None = None,
    settings: Settings | None = None,
) -> wc.ModelConfig:
    """Persist the LLM provider/model selection (raises ``ValueError`` if unsupported)."""
    return wc.set_model_config(provider, model, ollama_base_url, settings or load_settings())


def provider_status(settings: Settings | None = None) -> dict[str, dict[str, Any]]:
    """Report, per provider, whether it is currently usable and which is active."""
    settings = settings or load_settings()
    active = get_model_config(settings).provider
    return {
        "active": active,
        "providers": {
            "auto": {"available": True, "note": "Anthropic if configured, else Ollama, else local."},
            "local": {"available": True, "note": "Offline deterministic model. Always available."},
            "anthropic": {"available": anthropic_configured(), "note": "Requires ANTHROPIC_API_KEY."},
            "ollama": {"available": ollama_reachable(), "note": "Requires a running local Ollama server."},
            "openai": {"available": bool(os.getenv("OPENAI_API_KEY")), "note": "Requires OPENAI_API_KEY."},
        },
    }


def test_model_connection(settings: Settings | None = None) -> dict[str, Any]:
    """Run a tiny completion against the active model to verify connectivity."""
    settings = settings or load_settings()
    model = resolve_language_model(settings)
    try:
        completion = model.complete("Reply with a short confirmation that you are reachable.")
    except Exception as exc:  # pragma: no cover - provider/network specific
        return {"ok": False, "provider": model.provider, "model": model.model_id, "error": str(exc)}
    return {"ok": True, "provider": completion.provider, "model": completion.model_id, "text": completion.text[:200]}


# --- domain repositories -----------------------------------------------------


def list_domains(settings: Settings | None = None) -> list[wc.DomainRef]:
    """Return the configured domain↔git references."""
    return wc.list_domains(settings or load_settings())


def add_domain(
    label: str,
    remote_url: str,
    branch: str = "main",
    token_env: str | None = None,
    settings: Settings | None = None,
) -> wc.DomainRef:
    """Associate a domain of interest with the git repository its model lives in."""
    return wc.add_domain(label, remote_url, branch, token_env, settings=settings or load_settings())


def remove_domain(domain_id: str, settings: Settings | None = None) -> bool:
    """Remove a domain reference."""
    return wc.remove_domain(domain_id, settings or load_settings())


# --- governed authoring ------------------------------------------------------


def authoring_chat(
    domain_id: str | None,
    message: str,
    history: list[dict] | None = None,
    settings: Settings | None = None,
) -> AuthoringResult:
    """Hold a clarifying modelling conversation for a domain (or prompt for setup)."""
    return chat_turn(domain_id, message, history, settings=settings or load_settings())


def authoring_generate(
    domain_id: str,
    answers: InterviewAnswers,
    settings: Settings | None = None,
) -> AuthoringResult:
    """Scaffold, write and validate a domain model into its sandbox branch."""
    return author_model(domain_id, answers, settings=settings or load_settings())


def workspace_tree(domain_id: str, settings: Settings | None = None) -> list[str]:
    """Return the file tree of a domain's content repository (empty if uninitialised)."""
    settings = settings or load_settings()
    domain = wc.get_domain(domain_id, settings)
    if domain is None:
        return []
    repo = GitRepo(domain.local_path)
    return repo.tree() if repo.exists else []


def read_workspace_file(domain_id: str, relative_path: str, settings: Settings | None = None) -> str:
    """Return the content of a file in a domain's content repository."""
    settings = settings or load_settings()
    domain = wc.get_domain(domain_id, settings)
    if domain is None:
        raise KeyError(domain_id)
    return GitRepo(domain.local_path).read_file(relative_path)


def write_workspace_file(
    domain_id: str, relative_path: str, content: str, settings: Settings | None = None
) -> str:
    """Write a file in a domain's content repository and return its path."""
    settings = settings or load_settings()
    domain = wc.get_domain(domain_id, settings)
    if domain is None:
        raise KeyError(domain_id)
    repo = GitRepo.clone_or_open(domain.local_path, domain.remote_url)
    repo.checkout_branch(f"authoring/{domain_id}")
    return str(repo.write_file(relative_path, content))


def commit_and_open_pr(
    domain_id: str,
    title: str | None = None,
    body: str | None = None,
    settings: Settings | None = None,
) -> PullRequestRef:
    """Commit the domain's authoring branch and open (or link) a Pull Request."""
    return open_pr(domain_id, title=title, body=body, settings=settings or load_settings())


def advise(
    objective: str,
    candidate_type: str,
    criteria: list[Criterion],
    settings: Settings | None = None,
) -> AdvisoryResult:
    """Generic governed advisory: rank candidates of a type against weighted criteria.

    Pulls candidate resources of ``candidate_type`` from the local graph and returns an
    explainable, non-executing recommendation (``AdvisoryResult.ready`` is always ``False``).
    """
    settings = settings or load_settings()
    candidates = candidates_from_graph(candidate_type, criteria, settings=settings)
    return recommend(objective, candidates, criteria, settings=settings)


def fuseki_graph_triple_counts(
    graphs: list[str],
    settings: Settings | None = None,
    client: FusekiClient | None = None,
) -> dict[str, int]:
    """Return live triple counts for named graphs served by Fuseki.

    Each graph is queried against the dataset for its role, so counts are correct even
    when graphs live on different (local or remote) datasets. Used to confirm that
    materialized data is actually queryable from an available Apache Jena instance.
    Returns an empty mapping when Fuseki is unreachable so callers can degrade gracefully.
    Pass ``client`` to force every graph onto one dataset (used in tests).
    """
    settings = settings or load_settings()
    clients: dict[str, FusekiClient] = {}

    def client_for(graph_uri: str) -> FusekiClient:
        if client is not None:
            return client
        role = dataset_for_graph(graph_uri)
        if role not in clients:
            clients[role] = FusekiClient(settings=settings, dataset=role)
        return clients[role]

    health: dict[int, bool] = {}
    counts: dict[str, int] = {}
    for graph_uri in graphs:
        target_client = client_for(graph_uri)
        ok = health.get(id(target_client))
        if ok is None:
            ok = target_client.health_check().ok
            health[id(target_client)] = ok
        if not ok:
            continue
        response = target_client.execute_query(
            f"SELECT (COUNT(*) AS ?count) WHERE {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }}"
        )
        bindings = response.get("results", {}).get("bindings", [])
        counts[graph_uri] = int(bindings[0]["count"]["value"]) if bindings else 0
    return counts
