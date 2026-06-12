"""Governed conversational authoring of knowledge models (ADR-0016).

This subpackage lets a human, in conversation with an LLM, scaffold and edit the
RDF/mapping/data files that make up a domain knowledge model. Unlike the strictly
read-only agent assist (ADR-0013), authoring **writes files** — but only ever into
a sandboxed clone of a *separate, user-configured domain content repository*, on a
feature branch, validated, and surfaced as a Pull Request for a human to review and
merge. It never writes to the platform's authoritative graph or its own ``rdf/`` tree.
"""

from __future__ import annotations

from semantic_platform.authoring.workspace_config import (
    DomainRef,
    ModelConfig,
    add_domain,
    get_domain,
    get_model_config,
    list_domains,
    remove_domain,
    set_model_config,
)

__all__ = [
    "DomainRef",
    "ModelConfig",
    "add_domain",
    "get_domain",
    "get_model_config",
    "list_domains",
    "remove_domain",
    "set_model_config",
]
