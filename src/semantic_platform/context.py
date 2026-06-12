"""Domain data contexts: build a :class:`Settings` pointed at a domain's model.

The platform serves two data *contexts* through the same views (ADR-0018):

* **system** — the platform's own authoritative ``rdf/`` tree (the default).
* a **knowledge model** — a user-configured *domain* whose model lives in a separate
  git repository cloned under the workspace (see :mod:`semantic_platform.authoring`).

A knowledge-model context is nothing more than a :class:`Settings` whose RDF path
fields point at the domain repo's ``rdf/`` subtree (which mirrors the system layout).
Because every domain/``api`` function already accepts an optional ``settings``, the same
views render either context unchanged. This module is the single lever; it is
domain-neutral and never imports from ``app``.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from semantic_platform.authoring.gitrepo import GitRepo
from semantic_platform.authoring.workspace_config import get_domain
from semantic_platform.config import Settings, load_settings

#: Identifier of the default (platform self-model) context.
SYSTEM_CONTEXT = "system"


def domain_settings(domain_id: str, settings: Settings | None = None) -> Settings:
    """Return a :class:`Settings` whose RDF dirs point at a domain repo's ``rdf/`` tree.

    Ensures the domain repository is present (cloning/initialising it on first use, the
    same path the Studio uses). Non-RDF fields (Fuseki, workspace, LLM, output) are left
    untouched: a knowledge-model context only re-points the file-authored ``rdf/`` tree.

    Raises :class:`KeyError` when ``domain_id`` is not a configured domain, so the app
    layer can translate it into a 404. Missing ``rdf/`` subdirectories are tolerated —
    the graph loaders simply yield nothing, so an unscaffolded domain renders empty
    rather than erroring.
    """
    base = settings or load_settings()
    domain = get_domain(domain_id, base)
    if domain is None:
        raise KeyError(domain_id)
    local = Path(domain.local_path)
    GitRepo.clone_or_open(local, domain.remote_url)
    rdf_root = local / "rdf"
    return dataclasses.replace(
        base,
        rdf_root=rdf_root,
        ontology_dir=rdf_root / "ontology",
        vocabularies_dir=rdf_root / "vocabularies",
        data_dir=rdf_root / "data",
        shapes_dir=rdf_root / "shapes",
        queries_dir=rdf_root / "queries",
        graphs_dir=rdf_root / "graphs",
        default_query_file=rdf_root / "queries" / base.default_query_file.name,
    )
