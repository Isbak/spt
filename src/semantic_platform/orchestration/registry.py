"""Governed orchestration registry for workflow metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.orchestration.common import AGGOV, ORCH, local_id, text


class LifecycleStatus(StrEnum):
    """Supported governed lifecycle statuses."""

    DRAFT = "Draft"
    TESTING = "Testing"
    APPROVED = "Approved"
    DEPRECATED = "Deprecated"
    RETIRED = "Retired"


@dataclass(frozen=True)
class WorkflowRecord:
    """Registered workflow metadata."""

    workflow_id: str
    uri: str
    label: str
    owner: str
    steward: str
    lifecycle_state: str
    version: str
    approval_status: LifecycleStatus
    policies: tuple[str, ...]


class OrchestrationRegistry:
    """Read-only registry for governed workflows and templates."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = (
            graph
            if graph is not None
            else load_graph(
                [self.settings.vocabularies_dir, self.settings.data_dir], settings=self.settings
            )
        )

    def list_workflows(self) -> list[WorkflowRecord]:
        """Return all registered workflows."""
        workflows = sorted(set(self.graph.subjects(RDF.type, ORCH.Workflow)), key=str)
        return [self._record(URIRef(workflow)) for workflow in workflows]

    def get(self, workflow_id: str) -> WorkflowRecord | None:
        """Return a workflow by local id or URI."""
        for record in self.list_workflows():
            if workflow_id in {record.workflow_id, record.uri}:
                return record
        return None

    def require(self, workflow_id: str) -> WorkflowRecord:
        """Return one workflow or raise ``KeyError``."""
        record = self.get(workflow_id)
        if record is None:
            raise KeyError(f"Workflow is not registered: {workflow_id}")
        return record

    def validate(self) -> list[str]:
        """Return governance validation errors for registered workflows."""
        errors: list[str] = []
        for record in self.list_workflows():
            if not record.owner:
                errors.append(f"{record.workflow_id} has no owner")
            if not record.steward:
                errors.append(f"{record.workflow_id} has no steward")
            if not record.version:
                errors.append(f"{record.workflow_id} has no version")
            if record.approval_status not in set(LifecycleStatus):
                errors.append(f"{record.workflow_id} has unsupported approval status")
            if not record.policies:
                errors.append(f"{record.workflow_id} has no policy reference")
        if not self.list_workflows():
            errors.append("orchestration registry contains no workflows")
        return errors

    def _record(self, uri: URIRef) -> WorkflowRecord:
        status = text(self.graph, uri, AGGOV.approvalStatus, LifecycleStatus.DRAFT.value)
        return WorkflowRecord(
            workflow_id=local_id(uri),
            uri=str(uri),
            label=text(self.graph, uri, RDFS.label, local_id(uri)),
            owner=text(self.graph, uri, AGGOV.owner),
            steward=text(self.graph, uri, AGGOV.steward),
            lifecycle_state=text(self.graph, uri, ORCH.lifecycleState, "Draft"),
            version=text(self.graph, uri, OWL.versionInfo),
            approval_status=LifecycleStatus(status),
            policies=tuple(sorted(str(p) for p in self.graph.objects(uri, ORCH.governedByPolicy))),
        )
