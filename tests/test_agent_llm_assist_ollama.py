"""Prompt/eval tests against the REAL self-contained local LLM (Ollama).

These are not simulated — they drive a genuine local model served by the bundled
Ollama service. A multi-GB model cannot run in hermetic CI, so the tests are
**opt-in and skipped by default** (the same pattern as the real-Fuseki test).

To run them:

    make docker-up-llm                                   # start the ollama service
    docker exec semantic-platform-ollama ollama pull llama3.2
    RUN_OLLAMA_E2E=1 LLM_PROVIDER=ollama \
        python -m pytest tests/test_agent_llm_assist_ollama.py

Real-LLM output is non-deterministic, so the assertions check robust properties
and the governance invariants (which hold regardless of the model's wording) —
not exact text.
"""

from __future__ import annotations

import dataclasses
import os

import pytest
from rdflib import URIRef
from rdflib.namespace import PROV

from semantic_platform.agents.assist import ASSIST, generate_explanation
from semantic_platform.config import load_settings

AGENT_ID = "semantic-context-agent"


def _ollama_ready() -> bool:
    """True only when explicitly enabled and a live Ollama server answers."""
    if os.getenv("RUN_OLLAMA_E2E") != "1":
        return False
    import requests

    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    try:
        return requests.get(f"{base}/api/tags", timeout=2).ok
    except requests.RequestException:
        return False


def _ollama_settings():
    return dataclasses.replace(
        load_settings(),
        llm_provider="ollama",
        llm_model=os.getenv("LLM_MODEL") or "llama3.2",
    )


pytestmark = pytest.mark.skipif(
    not _ollama_ready(),
    reason="Set RUN_OLLAMA_E2E=1 with a running Ollama (make docker-up-llm + pull a model).",
)


def test_real_ollama_explanation_is_governed_and_recorded():
    result = generate_explanation(
        AGENT_ID,
        "reference",
        "Summarize the reference vocabulary in one sentence.",
        settings=_ollama_settings(),
    )
    # The real model actually produced a non-trivial answer.
    assert result.provider == "ollama"
    assert result.fact_count > 0
    assert len(result.text.strip()) > 10

    # Governance invariants hold regardless of the model's wording.
    activity = URIRef(result.explanation_iri)
    assert (activity, ASSIST.usedModel, None) in result.provenance
    associated = set(result.provenance.objects(activity, PROV.wasAssociatedWith))
    assert any("semantic-context-agent" in str(a) for a in associated)


def test_real_ollama_still_denies_unreadable_scope():
    # Permission is enforced before the model is ever called, even for a real provider.
    with pytest.raises(PermissionError):
        generate_explanation(AGENT_ID, "transactional", "Show me transactions", settings=_ollama_settings())
