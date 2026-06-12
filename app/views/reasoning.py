"""Reasoning views: status, inferences, consistency, explanations, rules, analytics.

All reasoning views run over the active context's graph, *except* the governed rule
registry: reasoning rules are platform-wide (cross-domain), so the Rules view always
shows the system rules regardless of the active context.
"""

from __future__ import annotations

from flask import g, render_template
from rdflib.namespace import RDFS

from app.visualizations.analytics_view import analytics_dashboard_data
from app.visualizations.reasoning_view import explanations_data, reasoning_dashboard_data
from semantic_platform.reasoning import reasoning_summary, run_reasoning
from semantic_platform.rule_registry import load_rule_registry


def index(scope=None):
    """Render reasoning engine status and statistics."""
    scope = scope or g.scope
    return render_template("reasoning.html", summary=reasoning_summary(settings=scope.settings))


def inferences(scope=None):
    """Render inferred assertions."""
    scope = scope or g.scope
    run = run_reasoning(settings=scope.settings)
    triples = sorted(run.inferred_graph, key=lambda triple: tuple(map(str, triple)))
    return render_template("inferences.html", triples=triples)


def legacy_explanations(scope=None):
    """Render generated inference explanations (legacy RDFS comment view)."""
    scope = scope or g.scope
    run = run_reasoning(settings=scope.settings)
    rows = []
    for inference in sorted(run.reasoning_graph.subjects(), key=str):
        for comment in run.reasoning_graph.objects(inference, RDFS.comment):
            rows.append({"resource": str(inference), "comment": str(comment)})
    return render_template("explanations.html", rows=rows)


def consistency(scope=None):
    """Render the semantic consistency report."""
    scope = scope or g.scope
    run = run_reasoning(settings=scope.settings)
    return render_template("consistency.html", report=run.consistency)


def rules(scope=None):
    """Render the governed reasoning rules (always system-wide, cross-domain)."""
    return render_template("rules.html", rules=load_rule_registry().all())


def dashboard(scope=None):
    """Render the reasoning explainability dashboard."""
    scope = scope or g.scope
    return render_template("reasoning_dashboard.html", data=reasoning_dashboard_data(settings=scope.settings))


def explanations(scope=None):
    """Render detailed, explainable inference assertions."""
    scope = scope or g.scope
    return render_template("explanation_explorer.html", rows=explanations_data(settings=scope.settings))


def analytics(scope=None):
    """Render the graph analytics dashboard."""
    scope = scope or g.scope
    return render_template("analytics.html", metrics=analytics_dashboard_data(settings=scope.settings))
