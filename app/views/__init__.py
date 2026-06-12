"""Context-agnostic view render functions shared by the System and Knowledge Model trees.

Each function takes the active :class:`~app.context_scope.ContextScope` (falling back to
``g.scope``) and renders a view from ``scope.settings`` — so the *same* logic serves both
the platform self-model (System) and a selected domain (Knowledge Model). The two
blueprint trees (``app.routes`` for System, ``app.contexts.knowledge_model`` for KM) bind
these functions to their respective endpoints; divergence later means a tree stops
sharing one function, not threading context flags through shared code.
"""
