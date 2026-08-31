"""Lightweight custom admin used by both apps.

The engine (blueprint, generic list/create/edit/delete routes, templates, CSS)
lives here; each app builds its own :class:`AdminSite` in ``website/admin.py``,
registers its models with :class:`Field` specs, and calls ``site.init_app(app)``.
"""

from .site import AdminSite, Field

__all__ = ["AdminSite", "Field"]
