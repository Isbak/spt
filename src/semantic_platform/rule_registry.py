"""Reasoning rule registration, governance, and lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass, replace

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph

REASON = Namespace("https://example.org/semantic-platform/reasoning#")
GOV = Namespace("https://example.org/semantic-platform/governance#")

ACTIVE_STATUSES = {"Approved", "Active", str(REASON.Approved), str(GOV.approved)}
BLOCKED_STATUSES = {"Deprecated", "Retired", str(REASON.Deprecated), str(REASON.Retired)}


@dataclass(frozen=True)
class Rule:
    """Governed rule metadata."""

    iri: URIRef
    label: str
    version: str
    owner: str
    steward: str
    status: str
    enabled: bool = True

    @property
    def executable(self) -> bool:
        """Return whether the rule is enabled and not deprecated/retired."""
        return self.enabled and self.status not in BLOCKED_STATUSES


class RuleRegistry:
    """In-memory registry backed by RDF rule metadata."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self._rules = {rule.iri: rule for rule in rules or []}

    def register(self, rule: Rule) -> None:
        """Register or replace a rule."""
        self._rules[rule.iri] = rule

    def enable(self, iri: URIRef) -> None:
        """Enable a registered rule."""
        self._rules[iri] = replace(self._rules[iri], enabled=True)

    def disable(self, iri: URIRef) -> None:
        """Disable a registered rule."""
        self._rules[iri] = replace(self._rules[iri], enabled=False)

    def all(self) -> list[Rule]:
        """Return all registered rules sorted by IRI."""
        return [self._rules[key] for key in sorted(self._rules, key=str)]

    def executable(self) -> list[Rule]:
        """Return enabled rules that are not deprecated or retired."""
        return [rule for rule in self.all() if rule.executable]


def _text(graph: Graph, subject: URIRef, predicate: URIRef, default: str = "") -> str:
    value = graph.value(subject, predicate)
    if isinstance(value, URIRef):
        label = graph.value(value, RDFS.label)
        return str(label or value)
    return str(value) if value is not None else default


def load_rule_registry(settings: Settings | None = None, graph: Graph | None = None) -> RuleRegistry:
    """Load governed rule definitions from RDF."""
    settings = settings or load_settings()
    graph = graph or load_graph([settings.vocabularies_dir, settings.data_dir], settings=settings)
    registry = RuleRegistry()
    for rule in sorted(graph.subjects(RDF.type, REASON.Rule), key=str):
        status = _text(graph, rule, REASON.ruleStatus, "Draft")
        registry.register(
            Rule(
                iri=rule,
                label=_text(graph, rule, RDFS.label, str(rule)),
                version=_text(graph, rule, OWL.versionInfo, "0.0.0"),
                owner=_text(graph, rule, REASON.ruleOwner, "Unassigned"),
                steward=_text(graph, rule, REASON.ruleSteward, "Unassigned"),
                status=status,
                enabled=status not in {"Deprecated", "Retired"},
            )
        )
    return registry
