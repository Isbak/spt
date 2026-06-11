"""Agent team registry with governance metadata."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.multi_agent.common import AGGOV, MA, bind, local_id, text


@dataclass(frozen=True)
class AgentTeamRecord:
    team_id: str
    uri: str
    label: str
    owner: str
    steward: str
    approval_status: str
    roles: tuple[str, ...]
    responsibilities: tuple[str, ...]


class AgentTeamRegistry:
    """Read and create governed multi-agent team records."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph if graph is not None else load_graph([self.settings.vocabularies_dir, self.settings.data_dir], settings=self.settings)
        bind(self.graph)

    def register_team(
        self,
        label: str,
        *,
        owner: str,
        steward: str,
        approval_status: str = "Approved",
        roles: tuple[str, ...] = (),
        responsibilities: tuple[str, ...] = (),
    ) -> AgentTeamRecord:
        team = URIRef(MA[f"team-{label.lower().replace(' ', '-')}"])
        self.graph.add((team, RDF.type, MA.AgentTeam))
        self.graph.add((team, RDFS.label, Literal(label)))
        self.graph.add((team, AGGOV.owner, Literal(owner)))
        self.graph.add((team, AGGOV.steward, Literal(steward)))
        self.graph.add((team, AGGOV.approvalStatus, Literal(approval_status)))
        for role in roles:
            role_uri = URIRef(MA[role]) if not role.startswith("http") else URIRef(role)
            self.graph.add((role_uri, RDF.type, MA.AgentRole))
            self.graph.add((team, MA.hasRole, role_uri))
        for responsibility in responsibilities:
            self.graph.add((team, MA.responsibility, Literal(responsibility)))
        return self._record(team)

    def list_teams(self) -> list[AgentTeamRecord]:
        return [self._record(team) for team in sorted(set(self.graph.subjects(RDF.type, MA.AgentTeam)), key=str)]

    def validate_governance(self) -> list[str]:
        errors: list[str] = []
        for team in self.list_teams():
            if not team.owner:
                errors.append(f"{team.team_id} has no owner")
            if not team.steward:
                errors.append(f"{team.team_id} has no steward")
            if team.approval_status != "Approved":
                errors.append(f"{team.team_id} is not approved")
            if not team.roles:
                errors.append(f"{team.team_id} has no roles")
        if not self.list_teams():
            errors.append("no agent teams registered")
        return errors

    def _record(self, team: URIRef) -> AgentTeamRecord:
        roles = tuple(local_id(role) for role in self.graph.objects(team, MA.hasRole))
        responsibilities = tuple(str(value) for value in self.graph.objects(team, MA.responsibility))
        return AgentTeamRecord(
            local_id(team), str(team), text(self.graph, team, RDFS.label, local_id(team)), text(self.graph, team, AGGOV.owner), text(self.graph, team, AGGOV.steward), text(self.graph, team, AGGOV.approvalStatus), roles, responsibilities
        )
