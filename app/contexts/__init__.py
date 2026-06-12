"""Context trees: System (``app.routes``) and Knowledge Model (this package).

Both trees bind the shared :mod:`app.views` render functions to blueprint endpoints; the
Knowledge Model tree mounts them under ``/model/<domain_id>/`` so a configured domain can
be inspected from every angle (ADR-0018).
"""
