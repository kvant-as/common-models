"""Shared session UI: the idle countdown + auto-logout used on every page,
and an enPlans-style "Сессии" card partial for profile pages.

Wire it up in ``create_app``::

    from common_models.session_ui import init_session_ui
    init_session_ui(app)

then drop ``{{ cm_session_guard() }}`` before ``</body>`` in the base template,
and ``{% include "cm_session/section.html" %}`` on the profile page.
"""

from flask import Blueprint, current_app, jsonify, url_for
from flask_login import current_user, login_required
from markupsafe import Markup

from .sessions import build_session_info, get_or_refresh_session, set_session_cookie

__all__ = ["init_session_ui"]

_bp = Blueprint(
    "cm_session", __name__,
    template_folder="session_ui_assets/templates",
    static_folder="session_ui_assets/static",
    static_url_path="/cm-session-static",
)


def _logout_endpoint():
    return current_app.config.get("SESSION_LOGOUT_ENDPOINT", "auth.logout")


@_bp.route("/session-info")
@login_required
def session_info():
    """Current session state for the guard script; reading it also refreshes
    the idle token (counts as activity), like any other request."""
    token, payload = get_or_refresh_session(current_user)
    info = build_session_info(current_user, payload)
    resp = jsonify({"success": True, "logout_url": url_for(_logout_endpoint()), **info})
    return set_session_cookie(resp, token)


def init_session_ui(app, url_prefix="/_session"):
    if "cm_session" not in app.blueprints:
        app.register_blueprint(_bp, url_prefix=url_prefix)

    @app.context_processor
    def _inject():
        def cm_session_guard():
            if not current_user.is_authenticated:
                return Markup("")
            return Markup(
                '<script src="{src}" data-info-url="{info}" '
                'data-logout-url="{logout}" defer></script>'.format(
                    src=url_for("cm_session.static", filename="session-guard.js"),
                    info=url_for("cm_session.session_info"),
                    logout=url_for(_logout_endpoint()),
                )
            )

        def cm_session_info():
            if not current_user.is_authenticated:
                return None
            _token, payload = get_or_refresh_session(current_user)
            info = build_session_info(current_user, payload)
            info["logout_url"] = url_for(_logout_endpoint())
            return info

        return {"cm_session_guard": cm_session_guard, "cm_session_info": cm_session_info}
