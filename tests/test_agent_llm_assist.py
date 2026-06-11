"""Tests for the governed, read-only agent LLM assist."""

from __future__ import annotations

import dataclasses
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from rdflib import URIRef
from rdflib.namespace import PROV, RDF

from app.app import create_app
from semantic_platform.agents.assist import ASSIST, generate_explanation
from semantic_platform.agents.llm import (
    AnthropicModel,
    LanguageModel,
    LLMCompletion,
    LocalDeterministicModel,
    OllamaModel,
    OpenAIModel,
    resolve_language_model,
)
from semantic_platform.config import load_settings

AGENT_ID = "semantic-context-agent"


# --- Provider resolution & the free offline default ---------------------------


def test_local_model_is_the_default_and_deterministic():
    model = resolve_language_model(load_settings())
    assert isinstance(model, LocalDeterministicModel)
    prompt = "Question: q\n- fact one\n- fact two"
    first = model.complete(prompt)
    second = model.complete(prompt)
    assert first == second  # deterministic
    assert first.provider == "local"
    assert "fact one" in first.text


def test_resolve_selects_external_providers_without_importing_sdks():
    base = load_settings()
    assert isinstance(resolve_language_model(dataclasses.replace(base, llm_provider="anthropic")), AnthropicModel)
    assert isinstance(resolve_language_model(dataclasses.replace(base, llm_provider="openai")), OpenAIModel)
    assert isinstance(resolve_language_model(dataclasses.replace(base, llm_provider="ollama")), OllamaModel)
    with pytest.raises(ValueError):
        resolve_language_model(dataclasses.replace(base, llm_provider="unknown"))


def test_anthropic_model_defaults_to_latest_opus():
    assert AnthropicModel().model_id == "claude-opus-4-8"


# --- Governed assist ----------------------------------------------------------


def test_generate_explanation_is_governed_and_records_provenance():
    result = generate_explanation(AGENT_ID, "reference", "What reference terms exist?")
    assert result.provider == "local"
    assert result.fact_count > 0
    assert result.text
    # Real self-contained (deterministic) model: the permitted facts flow into the
    # answer — IRIs from the reference scope appear in the explanation text.
    assert "http" in result.text

    prov = result.provenance
    activity = URIRef(result.explanation_iri)
    assert (activity, RDF.type, ASSIST.ExplanationActivity) in prov
    assert (activity, RDF.type, PROV.Activity) in prov
    assert (activity, ASSIST.usedModel, None) in prov
    # The explanation is attributed to the agent, not to a free-floating actor.
    associated = set(prov.objects(activity, PROV.wasAssociatedWith))
    assert any("semantic-context-agent" in str(a) for a in associated)


def test_generate_explanation_denies_unreadable_scope():
    # 'transactional' is not in the agent's allowed graph access list.
    with pytest.raises(PermissionError):
        generate_explanation(AGENT_ID, "transactional", "Show me transactions")


def test_injected_external_model_is_used_and_recorded():
    class _FakeExternalModel:
        provider = "anthropic"
        model_id = "claude-opus-4-8"

        def complete(self, prompt: str, *, system: str | None = None) -> LLMCompletion:
            assert "Facts the agent is permitted to read" in prompt
            return LLMCompletion(text="external answer", provider=self.provider, model_id=self.model_id)

    assert isinstance(_FakeExternalModel(), LanguageModel)
    result = generate_explanation(AGENT_ID, "reference", "explain", model=_FakeExternalModel())
    assert result.text == "external answer"
    assert result.provider == "anthropic"
    assert result.model_id == "claude-opus-4-8"
    assert (URIRef(result.explanation_iri), ASSIST.usedProvider, None) in result.provenance


# --- Bundled local Ollama provider — HTTP contract test -----------------------
# The real self-contained option is the `ollama` docker-compose service. CI can't
# run a multi-GB model, so (exactly as the Fuseki tests use a stand-in HTTP server)
# this exercises OllamaModel's real HTTP request/response contract in-process.


class _FakeOllamaHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode())
        payload = json.dumps({"response": f"echo[{body['model']}]: {body['prompt'][:20]}"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)


def test_ollama_provider_round_trip_against_local_server():
    server = HTTPServer(("127.0.0.1", 0), _FakeOllamaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        model = OllamaModel(base_url=f"http://127.0.0.1:{port}", model_id="llama3.2")
        completion = model.complete("Question: hello\n- fact")
        assert completion.provider == "ollama"
        assert completion.model_id == "llama3.2"
        assert completion.text.startswith("echo[llama3.2]:")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


# --- Flask route --------------------------------------------------------------


def test_explain_route_returns_explanation():
    client = create_app().test_client()
    response = client.get(f"/api/agents/{AGENT_ID}/explain?scope=reference&question=what")
    assert response.status_code == 200
    body = response.get_json()
    assert body["provider"] == "local"
    assert body["agent_id"] == AGENT_ID
    assert "text" in body


def test_explain_route_denies_unreadable_scope_with_403():
    client = create_app().test_client()
    response = client.get(f"/api/agents/{AGENT_ID}/explain?scope=transactional")
    assert response.status_code == 403
    assert "error" in response.get_json()
