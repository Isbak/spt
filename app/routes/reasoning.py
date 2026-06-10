"""Reasoning UI routes."""

from __future__ import annotations

from flask import Blueprint, render_template
from rdflib.namespace import RDFS

from semantic_platform.reasoning import reasoning_summary, run_reasoning
from semantic_platform.rule_registry import load_rule_registry

reasoning_bp = Blueprint("reasoning", __name__)


@reasoning_bp.get("/reasoning")
def reasoning_index():
    """Render reasoning engine status and statistics."""
    return render_template("reasoning.html", summary=reasoning_summary())


@reasoning_bp.get("/inferences")
def inferences_index():
    """Render inferred assertions."""
    run = run_reasoning()
    triples = sorted(run.inferred_graph, key=lambda triple: tuple(map(str, triple)))
    return render_template("inferences.html", triples=triples)


@reasoning_bp.get("/legacy-explanations")
def explanations_index():
    """Render generated inference explanations."""
    run = run_reasoning()
    rows = []
    for inference in sorted(run.reasoning_graph.subjects(), key=str):
        comments = list(run.reasoning_graph.objects(inference, RDFS.comment))
        for comment in comments:
            rows.append({"resource": str(inference), "comment": str(comment)})
    return render_template("explanations.html", rows=rows)


@reasoning_bp.get("/consistency")
def consistency_index():
    """Render semantic consistency report."""
    run = run_reasoning()
    return render_template("consistency.html", report=run.consistency)


@reasoning_bp.get("/rules")
def rules_index():
    """Render governed reasoning rules."""
    return render_template("rules.html", rules=load_rule_registry().all())
