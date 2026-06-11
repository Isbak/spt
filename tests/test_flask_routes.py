from app.app import create_app


class FakeStatus:
    ok = True
    status_code = 200
    message = "OK"


def test_flask_routes(monkeypatch):
    monkeypatch.setattr("app.routes.health.fuseki_health", lambda: FakeStatus())
    app = create_app()
    client = app.test_client()

    assert client.get("/").status_code == 200
    health = client.get("/health")
    assert health.status_code == 200
    assert health.get_json()["fuseki"]["ok"] is True
    assert client.get("/graphs").status_code == 200
    assert client.get("/ontology").status_code == 200
    assert client.get("/query").status_code == 200
    assert client.get("/governance").status_code == 200
    assert client.get("/provenance").status_code == 200
    assert client.get("/named-graphs").status_code == 200
    assert client.get("/ontology-version").status_code == 200
    assert client.get("/mappings").status_code == 200
    assert client.get("/source-catalog").status_code == 200
    assert client.get("/integration").status_code == 200
    assert client.get("/mapping-lineage").status_code == 200
    assert client.get("/reasoning").status_code == 200
    assert client.get("/inferences").status_code == 200
    assert client.get("/explanations").status_code == 200
    assert client.get("/legacy-explanations").status_code == 200
    assert client.get("/ontology-browser").status_code == 200
    assert client.get("/governance-dashboard").status_code == 200
    assert client.get("/provenance-explorer").status_code == 200
    assert client.get("/reasoning-dashboard").status_code == 200
    assert client.get("/analytics").status_code == 200
    assert client.get("/search?q=dataset").status_code == 200
    assert client.get("/consistency").status_code == 200
    assert client.get("/rules").status_code == 200
    assert client.get("/domain-models").status_code == 200
    assert client.get("/shapes").status_code == 200


def test_domain_import_route_success(monkeypatch):
    import io

    from semantic_platform.domain_models import ImportedFile, ImportResult

    captured = {}

    def fake_import(*, ontology=None, shape=None, mapping=None, settings=None):
        captured["ontology"] = ontology
        return ImportResult(
            ok=True,
            files=(ImportedFile("ontology", "widget.ttl", "/rdf/ontology/widget.ttl", True),),
            errors=(),
        )

    monkeypatch.setattr("app.routes.domain_models.import_domain", fake_import)
    app = create_app()
    response = app.test_client().post(
        "/domain-models/import",
        data={"ontology": (io.BytesIO(b"# turtle"), "widget.ttl")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"Imported" in response.data
    assert captured["ontology"][0] == "widget.ttl"


def test_domain_import_route_error(monkeypatch):
    from semantic_platform.domain_models import ImportResult

    monkeypatch.setattr(
        "app.routes.domain_models.import_domain",
        lambda **kwargs: ImportResult(ok=False, files=(), errors=("ontology (x.ttl): boom",)),
    )
    app = create_app()
    response = app.test_client().post("/domain-models/import", data={})
    assert response.status_code == 200
    assert b"Import failed" in response.data
    assert b"boom" in response.data


def test_query_route_executes_post(monkeypatch):
    monkeypatch.setattr(
        "app.routes.query.run_local_query",
        lambda query_text, settings: [{"metric": "entities", "value": "1"}],
    )
    app = create_app()
    response = app.test_client().post("/query", data={"query": "SELECT * WHERE {}"})
    assert response.status_code == 200
    assert b"entities" in response.data
