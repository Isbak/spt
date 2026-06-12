from pathlib import Path

from semantic_platform.config import load_settings
from semantic_platform.fuseki import FusekiClient


class FakeResponse:
    def __init__(self, ok=True, status_code=200, reason="OK", payload=None):
        self.ok = ok
        self.status_code = status_code
        self.reason = reason
        self._payload = payload or {"results": {"bindings": []}}

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(self.reason)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return FakeResponse()

    def put(self, url, **kwargs):
        self.calls.append(("put", url, kwargs))
        return FakeResponse()

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        return FakeResponse(payload={"head": {"vars": []}, "results": {"bindings": []}})


def test_fuseki_health_check_uses_base_url():
    session = FakeSession()
    status = FusekiClient(session=session).health_check()
    assert status.ok
    assert session.calls[0][0] == "get"
    assert session.calls[0][1] == "http://localhost:3030"


def test_fuseki_dataset_upload_and_query(tmp_path: Path):
    session = FakeSession()
    client = FusekiClient(session=session)
    ttl = tmp_path / "graph.ttl"
    ttl.write_text("@prefix ex: <https://example.org/> . ex:s ex:p ex:o .", encoding="utf-8")
    assert client.dataset_exists()
    client.upload_graph(ttl, "urn:test:graph")
    assert client.execute_query("ASK {}") == {"head": {"vars": []}, "results": {"bindings": []}}
    assert [call[0] for call in session.calls] == ["get", "put", "post"]


def test_default_dataset_is_system():
    client = FusekiClient(session=FakeSession())
    assert client.endpoint.dataset == "semantic-platform"


def test_dataset_arg_selects_role_endpoint():
    settings = load_settings()
    business = FusekiClient(settings=settings, session=FakeSession(), dataset="business")
    assert business.endpoint.dataset == "semantic-platform-business"
    assert business.endpoint.query_url.endswith("/semantic-platform-business/query")


def test_for_graph_routes_to_role_dataset():
    # An integration graph routes to business; an ontology graph to system.
    business = FusekiClient.for_graph("urn:graph:integration", session=FakeSession())
    system = FusekiClient.for_graph("urn:semantic-platform:graph:ontology", session=FakeSession())
    provenance = FusekiClient.for_graph("urn:graph:provenance", session=FakeSession())
    assert business.endpoint.dataset == "semantic-platform-business"
    assert system.endpoint.dataset == "semantic-platform"
    assert provenance.endpoint.dataset == "semantic-platform-agents"


def test_uploads_go_to_role_specific_dataset_path(tmp_path: Path):
    session = FakeSession()
    ttl = tmp_path / "g.ttl"
    ttl.write_text("@prefix ex: <https://example.org/> . ex:s ex:p ex:o .", encoding="utf-8")
    FusekiClient.for_graph("urn:graph:integration", session=session).upload_graph(ttl, "urn:graph:integration")
    FusekiClient.for_graph("urn:graph:ontology", session=session).upload_graph(ttl, "urn:graph:ontology")
    put_urls = [url for verb, url, _ in session.calls if verb == "put"]
    assert any("semantic-platform-business/data" in url for url in put_urls)
    assert any(url.endswith("/semantic-platform/data") for url in put_urls)


def test_auth_reads_from_endpoint_bundle(monkeypatch):
    monkeypatch.setenv("FUSEKI_BUSINESS_USERNAME", "u")
    monkeypatch.setenv("FUSEKI_BUSINESS_PASSWORD", "p")
    settings = load_settings()
    assert FusekiClient(settings=settings, session=FakeSession(), dataset="business").auth == ("u", "p")
    # System has no creds here, so it sends none.
    assert FusekiClient(settings=settings, session=FakeSession(), dataset="system").auth is None
