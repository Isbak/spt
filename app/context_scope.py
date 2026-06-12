"""The active data context for a request, bound to ``g`` by the app factory.

A :class:`ContextScope` bundles *which* :class:`Settings` the shared view render
functions read from, plus a tree-aware :meth:`ContextScope.url_for` so a single set of
templates can link within whichever tree (System or a Knowledge Model) is active:

* **System** scope → endpoints resolve to today's blueprints (``ontology.index``).
* **Knowledge Model** scope → endpoints resolve to the parallel ``model_*`` tree mounted
  under ``/model/<domain_id>/`` (``model_ontology.index`` with ``domain_id`` supplied).

Only ``scope.settings`` ever flows down into the package; HTTP/``g`` access stays here.
"""

from __future__ import annotations

from dataclasses import dataclass

from flask import url_for as flask_url_for

from semantic_platform.config import Settings
from semantic_platform.context import SYSTEM_CONTEXT


@dataclass(frozen=True)
class ContextScope:
    """The active context: its id, label, resolved settings, and link resolver."""

    context_id: str
    label: str
    settings: Settings
    is_system: bool

    def url_for(self, view: str, **values: object) -> str:
        """Resolve a logical (System) endpoint name into the active tree's URL.

        ``view`` is always the System endpoint name (e.g. ``"ontology.index"``). In a
        knowledge-model scope it is rewritten to ``"model_<blueprint>.<endpoint>"`` with
        the active ``domain_id`` injected, so shared templates need no branching.
        """
        if self.is_system:
            return flask_url_for(view, **values)
        blueprint, _, endpoint = view.partition(".")
        return flask_url_for(
            f"model_{blueprint}.{endpoint}", domain_id=self.context_id, **values
        )


def system_scope(settings: Settings) -> ContextScope:
    """Return the default System context scope."""
    return ContextScope(SYSTEM_CONTEXT, "System", settings, is_system=True)
