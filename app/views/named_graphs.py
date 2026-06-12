"""Named graph manifest view for the active context."""

from __future__ import annotations

from flask import g, render_template

from semantic_platform.named_graphs import graph_lifecycle_summary


def index(scope=None):
    """Render the named graph lifecycle summary."""
    scope = scope or g.scope
    return render_template("named_graphs.html", summary=graph_lifecycle_summary(settings=scope.settings))
