"""The Knowledge Model context tree: the same views, scoped to a selected domain."""

from __future__ import annotations

from app.contexts.knowledge_model.routes import knowledge_model_blueprints

__all__ = ["knowledge_model_blueprints"]
