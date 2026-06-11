"""Governed, read-only LLM assist for agents.

A human invokes :func:`generate_explanation` to have an agent explain or summarize
data **it is already permitted to read**. The flow is deliberately constrained:

* the agent is resolved from the registry and its read permission for the scope is
  enforced (via the same safety check the context provider uses);
* only the facts in the permitted scope are retrieved and passed to the model;
* the model produces text — it never selects tools, drives plans, or writes to the
  knowledge graph;
* a PROV-O record attributes the explanation to the agent and the model used.

The model is pluggable (:mod:`semantic_platform.agents.llm`); the default is a free,
offline deterministic model, so this capability is self-contained unless an external
provider is explicitly configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, XSD

from semantic_platform.agents.context import AgentContextProvider
from semantic_platform.agents.llm import LanguageModel, resolve_language_model
from semantic_platform.agents.registry import AgentRegistry
from semantic_platform.config import Settings, load_settings

ASSIST = Namespace("https://example.org/semantic-platform/agent-assist#")
MAX_FACTS = 50


@dataclass(frozen=True)
class ExplanationResult:
    """Outcome of a governed read-only explanation."""

    agent_id: str
    scope: str
    question: str
    provider: str
    model_id: str
    text: str
    fact_count: int
    explanation_iri: str
    provenance: Graph


def _facts(graph: Graph) -> list[str]:
    """Return a bounded, deterministic list of fact lines from a scope graph."""
    rendered = sorted(f"- {s} {p} {o}" for s, p, o in graph)
    return rendered[:MAX_FACTS]


def _build_prompt(scope: str, question: str, facts: list[str]) -> str:
    facts_block = "\n".join(facts) if facts else "- (no facts available)"
    return (
        f"Question: {question}\n"
        f"Scope: {scope}\n"
        f"Facts the agent is permitted to read:\n{facts_block}\n\n"
        "Answer the question using only the facts above."
    )


def _record_provenance(
    agent_uri: URIRef, scope: str, provider: str, model_id: str, fact_count: int
) -> tuple[Graph, URIRef]:
    graph = Graph()
    graph.bind("prov", PROV)
    graph.bind("assist", ASSIST)
    now = datetime.now(UTC).replace(microsecond=0)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    activity = URIRef(ASSIST[f"explanation-{scope}-{stamp}"])
    entity = URIRef(ASSIST[f"explanation-entity-{scope}-{stamp}"])
    graph.add((activity, RDF.type, ASSIST.ExplanationActivity))
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, PROV.wasAssociatedWith, agent_uri))
    graph.add((activity, ASSIST.usedProvider, Literal(provider)))
    graph.add((activity, ASSIST.usedModel, Literal(model_id)))
    graph.add((activity, ASSIST.scope, Literal(scope)))
    graph.add((activity, ASSIST.factCount, Literal(fact_count, datatype=XSD.integer)))
    graph.add((activity, PROV.endedAtTime, Literal(now.isoformat(), datatype=XSD.dateTime)))
    graph.add((entity, RDF.type, PROV.Entity))
    graph.add((entity, PROV.wasGeneratedBy, activity))
    graph.add((entity, PROV.wasAttributedTo, agent_uri))
    return graph, activity


def generate_explanation(
    agent_id: str,
    scope: str,
    question: str,
    *,
    settings: Settings | None = None,
    model: LanguageModel | None = None,
) -> ExplanationResult:
    """Generate a governed, read-only explanation for an agent over a scope.

    Raises ``PermissionError`` when the agent may not read ``scope``.
    """
    settings = settings or load_settings()
    agent = AgentRegistry(settings=settings).require(agent_id)

    # Enforces approval status + read permission for the scope; raises PermissionError.
    context = AgentContextProvider(settings).retrieve(agent, scope)
    facts = _facts(context.graph)

    model = model or resolve_language_model(settings)
    completion = model.complete(_build_prompt(scope, question, facts))

    provenance, activity = _record_provenance(
        URIRef(agent.uri), scope, completion.provider, completion.model_id, len(facts)
    )
    return ExplanationResult(
        agent_id=agent.agent_id,
        scope=scope,
        question=question,
        provider=completion.provider,
        model_id=completion.model_id,
        text=completion.text,
        fact_count=len(facts),
        explanation_iri=str(activity),
        provenance=provenance,
    )
