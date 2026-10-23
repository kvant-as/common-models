"""Resolving "which application is this" against the Application table.

Each Flask app already identifies itself via ``app.config["APP_NAME"]``
('erespondentn' | 'enplans' — same string used in UserAppActivity.app). This
module maps that string to the corresponding :class:`Application` row/id so
account-scoping code (login, registration, admin backfill) doesn't need to
hardcode ids.

The id is cached on ``current_app.config`` after the first lookup per
process — it's immutable for the lifetime of the app, so one query is enough.
"""

from flask import current_app

from .models import db, Application
from .logs import get_logger

__all__ = ["get_current_application", "get_current_application_id"]

_CACHE_KEY = "_CURRENT_APPLICATION_ID"


def get_current_application(app_code=None):
    """Return the :class:`Application` row for ``app_code`` (defaults to
    ``current_app.config["APP_NAME"]``), or ``None`` if it isn't seeded yet."""
    code = app_code or current_app.config.get("APP_NAME")
    if not code:
        return None
    try:
        return Application.query.filter_by(code=code).first()
    except Exception:
        get_logger().warning("get_current_application failed", exc_info=True)
        return None


def get_current_application_id(app_code=None):
    """Return the id of the current application, cached on
    ``current_app.config`` after the first successful lookup. Returns
    ``None`` if the Application row doesn't exist (e.g. migration not yet
    applied/seeded) — callers should treat that as "scoping unavailable",
    not crash the request."""
    if app_code is None and current_app.config.get(_CACHE_KEY) is not None:
        return current_app.config[_CACHE_KEY]

    application = get_current_application(app_code)
    if application is None:
        return None

    if app_code is None:
        current_app.config[_CACHE_KEY] = application.id

    return application.id
