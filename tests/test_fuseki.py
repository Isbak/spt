from pathlib import Path

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
