"""Apache Jena Fuseki integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import logging

import requests

from semantic_platform.config import FusekiDataset, Settings, load_settings
from semantic_platform.named_graphs import dataset_for_graph

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FusekiStatus:
    """Fuseki status check result."""

    ok: bool
    status_code: int | None
    message: str


class FusekiClient:
    """Small, testable client bound to one Fuseki dataset (storage role).

    Pass ``dataset`` to select a role bundle (``system``/``agents``/``business``) from
    settings, or ``endpoint`` to bind to an explicit :class:`FusekiDataset`. Defaults to
    the ``system`` role, which preserves the historic single-dataset behavior.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        session: requests.Session | None = None,
        timeout: float = 5.0,
        *,
        dataset: str = "system",
        endpoint: FusekiDataset | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.session = session or requests.Session()
        self.timeout = timeout
        self.endpoint = endpoint or self.settings.fuseki(dataset)

    @classmethod
    def for_graph(cls, graph_uri: str, settings: Settings | None = None, **kwargs: Any) -> FusekiClient:
        """Return a client bound to the dataset that serves ``graph_uri``."""
        settings = settings or load_settings()
        return cls(settings=settings, dataset=dataset_for_graph(graph_uri), **kwargs)

    @property
    def auth(self) -> tuple[str, str] | None:
        if self.endpoint.username and self.endpoint.password:
            return (self.endpoint.username, self.endpoint.password)
        return None

    def health_check(self) -> FusekiStatus:
        """Check whether the Fuseki HTTP service responds."""
        try:
            response = self.session.get(self.endpoint.base_url, timeout=self.timeout)
            return FusekiStatus(response.ok, response.status_code, response.reason)
        except requests.RequestException as exc:
            LOGGER.warning("Fuseki health check failed: %s", exc)
            return FusekiStatus(False, None, str(exc))

    def dataset_exists(self) -> bool:
        """Check whether the configured dataset endpoint exists."""
        try:
            response = self.session.get(self.endpoint.dataset_url, timeout=self.timeout, auth=self.auth)
            return response.status_code in {200, 303}
        except requests.RequestException as exc:
            LOGGER.warning("Fuseki dataset check failed: %s", exc)
            return False

    def upload_graph(self, file_path: Path, graph_uri: str) -> None:
        """Upload a Turtle graph using the Graph Store Protocol."""
        data = file_path.read_bytes()
        response = self.session.put(
            self.endpoint.data_url,
            params={"graph": graph_uri},
            data=data,
            headers={"Content-Type": "text/turtle"},
            timeout=self.timeout,
            auth=self.auth,
        )
        response.raise_for_status()
        LOGGER.info("Uploaded %s to graph %s", file_path, graph_uri)

    def execute_query(self, query_text: str) -> dict[str, Any]:
        """Execute a SPARQL query against Fuseki and return JSON results."""
        response = self.session.post(
            self.endpoint.query_url,
            data={"query": query_text},
            headers={"Accept": "application/sparql-results+json"},
            timeout=self.timeout,
            auth=self.auth,
        )
        response.raise_for_status()
        return response.json()
