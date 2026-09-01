"""Shared session / idle-timeout handling for the kvant-as apps.

Model
-----
* A **JWT cookie** (``SESSION_TOKEN_COOKIE``) binds the browser to a login.
  It only carries ``user_id`` / ``session_id`` / ``created_at`` / ``exp`` and
  lives for ``SESSION_DURATION`` (a hard 7-day cap). It is *not* where the
  idle timeout lives.
* The **idle timeout** is driven entirely by ``UserAppActivity.last_active``
  for ``(user, APP_NAME)`` compared against the role's allowed idle time
  (:func:`get_user_session_timeout`). One source of truth, per application.
* :func:`enforce_idle_timeout` installs a single ``before_request`` guard that
  logs the user out once that window is exceeded — on every page, not just
  ``@session_required`` ones. It also slides the window, but **only for real
  user activity**: a page navigation or a normal server call. Requests under
  ``SESSION_ACTIVITY_IGNORE_PREFIXES`` (``/api`` data loads, the session/forms
  helper endpoints) and pure client-side things like scrolling never extend
  the session.

Config (``app.config``)
-----------------------
==================================  =====================================  =========================================
Key                                 Default                                Meaning
==================================  =====================================  =========================================
``APP_NAME``                         --                                     Scopes activity to this app (required).
``SESSION_TOKEN_COOKIE``             ``session_token``                      Idle-token cookie name.
``SESSION_TOKEN_COOKIE_SECURE``      ``False``                              Set ``True`` in production (HTTPS).
``SESSION_TIMEOUT_PRIVILEGED``       ``timedelta(hours=9)``                 Idle window for privileged users.
``SESSION_TIMEOUT_DEFAULT``          ``timedelta(minutes=60)``              Idle window for everyone else.
``SESSION_PRIVILEGED_ATTRS``         ``('is_admin','is_auditor',
                                       'is_approver','is_reader')``         User flags that grant the long window.
``SESSION_ACTIVITY_IGNORE_PREFIXES`` ``('/api','/_session','/_forms')``     Path prefixes that do NOT slide the window.
``SESSION_ACTIVITY_WRITE_INTERVAL``  ``45``                                 Min seconds between activity-row writes.
``SESSION_LOGIN_ENDPOINT``           ``views.login``                        Where to send a logged-out user.
``SESSION_LOGOUT_ENDPOINT``          ``auth.logout``                        Logout endpoint (never guarded).
``SESSION_DEFAULT_REDIRECT``         ``views.profile``                      Default target of ``create_login_response``.
``SESSION_ENFORCE_IN_DEBUG``         ``False``                              Keep enforcing the timeout under ``app.debug``.
==================================  =====================================  =========================================
"""

import time
import uuid
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import (
    current_app, flash, jsonify, make_response, redirect, request, url_for,
)
from flask_login import current_user
from user_agents import parse

from .activity import get_app_last_active, touch_user_activity
from .models import User
from .timeutils import current_utc_time

__all__ = [
    "JWT_ALGORITHM",
    "SESSION_DURATION",
    "get_user_session_timeout",
    "get_session_time_left",
    "create_session_token",
    "set_session_cookie",
    "create_login_response",
    "verify_session_token",
    "get_session_from_cookie",
    "update_session_activity",
    "describe_device",
    "build_session_info",
    "get_or_refresh_session",
    "force_logout",
    "session_required",
    "enforce_idle_timeout",
    "get_current_user",
    "clear_session_cookie",
]

JWT_ALGORITHM = "HS256"
SESSION_DURATION = timedelta(days=7)          # hard cap on the JWT cookie
_TOKEN_RENEW_WITHIN = timedelta(days=1)       # re-issue the cookie when this close to exp
_DEFAULT_PRIVILEGED_ATTRS = ("is_admin", "is_auditor", "is_approver", "is_reader")
_DEFAULT_IGNORE_PREFIXES = ("/api", "/_session", "/_forms")


# --------------------------------------------------------------------------- #
#  small helpers
# --------------------------------------------------------------------------- #

def _cfg(key, default):
    return current_app.config.get(key, default)


def _cookie_name():
    return _cfg("SESSION_TOKEN_COOKIE", "session_token")


def _as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _naive(dt):
    if dt is not None and getattr(dt, "tzinfo", None) is not None:
        return dt.replace(tzinfo=None)
    return dt


def _enforcing():
    """Whether the idle timeout is actually acted on right now."""
    if not current_app.debug:
        return True
    return _as_bool(_cfg("SESSION_ENFORCE_IN_DEBUG", False))


def _ignore_prefixes():
    return tuple(_cfg("SESSION_ACTIVITY_IGNORE_PREFIXES", _DEFAULT_IGNORE_PREFIXES))


def _is_activity_request():
    """True when the current request should slide the idle window: a real page
    navigation or server action, not an ``/api`` poll or a helper endpoint."""
    path = request.path or "/"
    if any(path.startswith(p) for p in _ignore_prefixes()):
        return False
    endpoint = request.endpoint or ""
    if endpoint.rsplit(".", 1)[-1] == "static":
        return False
    return True


def _wants_json():
    path = request.path or ""
    if path.startswith("/api"):
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    accept = request.accept_mimetypes
    return accept["application/json"] >= accept["text/html"] and accept["application/json"] > 0


def get_user_session_timeout(user):
    attrs = _cfg("SESSION_PRIVILEGED_ATTRS", _DEFAULT_PRIVILEGED_ATTRS)
    if any(getattr(user, attr, False) for attr in attrs):
        return _cfg("SESSION_TIMEOUT_PRIVILEGED", timedelta(hours=9))
    return _cfg("SESSION_TIMEOUT_DEFAULT", timedelta(minutes=60))


# --------------------------------------------------------------------------- #
#  JWT idle-token
# --------------------------------------------------------------------------- #

def create_session_token(user):
    now = current_utc_time()
    payload = {
        "user_id": user.id,
        "session_id": str(uuid.uuid4()),
        "created_at": now.isoformat(),
        "exp": (now + SESSION_DURATION).timestamp(),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=JWT_ALGORITHM)


def verify_session_token(token):
    if not token:
        return None
    try:
        return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError as exc:
        current_app.logger.debug("invalid session token: %s", exc)
        return None


def update_session_activity(token):
    """Kept for API compatibility. The token no longer carries a ``last_active``
    claim, so this just re-issues it with a fresh ``exp`` (slides the 7-day cap)
    or returns ``None`` if the token is unusable."""
    payload = verify_session_token(token)
    if not payload:
        return None
    now = current_utc_time()
    payload["exp"] = (now + SESSION_DURATION).timestamp()
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=JWT_ALGORITHM)


def set_session_cookie(response, token):
    response.set_cookie(
        _cookie_name(),
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=_as_bool(_cfg("SESSION_TOKEN_COOKIE_SECURE", False)),
        samesite="Lax",
        path="/",
    )
    return response


def clear_session_cookie(response):
    response.delete_cookie(_cookie_name(), path="/")
    return response


def get_session_from_cookie():
    return verify_session_token(request.cookies.get(_cookie_name()))


def create_login_response(user, redirect_endpoint=None):
    endpoint = redirect_endpoint or _cfg("SESSION_DEFAULT_REDIRECT", "views.profile")
    response = make_response(redirect(url_for(endpoint)))
    return set_session_cookie(response, create_session_token(user))


def get_or_refresh_session(user):
    """Return ``(token, payload)`` for the current browser, minting or renewing
    the cookie token as needed. No activity side effects."""
    token = request.cookies.get(_cookie_name())
    payload = verify_session_token(token)

    if not payload:
        token = create_session_token(user)
        return token, verify_session_token(token)

    if payload.get("exp", 0) - time.time() <= _TOKEN_RENEW_WITHIN.total_seconds():
        token = update_session_activity(token) or token
        payload = verify_session_token(token) or payload

    return token, payload


# --------------------------------------------------------------------------- #
#  UI helpers
# --------------------------------------------------------------------------- #

def describe_device(ua_string):
    try:
        ua = parse(ua_string or "")
        browser = ua.browser.family or "Браузер"
        os_name = ua.os.family or ""
        return f"{browser} · {os_name}".strip(" ·") or "Неизвестное устройство"
    except Exception:                                     # noqa: BLE001
        return "Неизвестное устройство"


def _role_label(user):
    if getattr(user, "is_admin", False):
        return "Администратор"
    if getattr(user, "is_auditor", False):
        return "Аудитор"
    if getattr(user, "is_approver", False):
        return "Утверждающий"
    if getattr(user, "is_reader", False):
        return "Читатель"
    return "Респондент"


def build_session_info(user, payload=None):
    """State for the profile 'Сессия' card and the ``/session-info`` endpoint.
    ``last_active`` / ``expires_at`` come from the real per-app activity row."""
    now = current_utc_time()
    timeout = get_user_session_timeout(user)

    created_at = now
    if payload and payload.get("created_at"):
        try:
            created_at = datetime.fromisoformat(payload["created_at"])
        except (TypeError, ValueError):
            pass

    last_active = _naive(get_app_last_active(user.id, _cfg("APP_NAME", None))) or _naive(now)

    return {
        "role_label": _role_label(user),
        "timeout_minutes": int(timeout.total_seconds() // 60),
        "created_at": created_at.isoformat(),
        "last_active": last_active.isoformat(),
        "expires_at": (last_active + timeout).isoformat(),
        "server_time": _naive(now).isoformat(),
        "device": describe_device(request.headers.get("User-Agent", "")),
        "ip": request.remote_addr or "",
    }


def get_session_time_left():
    """``(seconds_left, timeout_seconds)`` for the header timer, or ``None``."""
    if not current_user.is_authenticated:
        return None
    user = current_user._get_current_object()
    timeout = get_user_session_timeout(user)
    last = _naive(get_app_last_active(user.id, _cfg("APP_NAME", None))) or _naive(current_utc_time())
    left = (timeout - (_naive(current_utc_time()) - last)).total_seconds()
    return max(0, int(left)), int(timeout.total_seconds())


# --------------------------------------------------------------------------- #
#  logout / guards
# --------------------------------------------------------------------------- #

def _login_redirect():
    resp = make_response(redirect(url_for(_cfg("SESSION_LOGIN_ENDPOINT", "views.login"))))
    return clear_session_cookie(resp)


def force_logout():
    flash("Сессия недействительна или истекла. Пожалуйста, войдите снова", "error")
    return _login_redirect()


def session_required(view_func):
    """Require an authenticated user (redirecting anonymous visitors to the
    login endpoint) and make sure the idle-token cookie exists. The idle
    timeout itself is enforced globally by :func:`enforce_idle_timeout`."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if current_app.debug and not _enforcing():
                return view_func(*args, **kwargs)
            return _login_redirect()

        if verify_session_token(request.cookies.get(_cookie_name())):
            return view_func(*args, **kwargs)

        # Flask-Login session is valid but our cookie is missing/expired.
        token = create_session_token(current_user._get_current_object())
        response = make_response(view_func(*args, **kwargs))
        return set_session_cookie(response, token)

    return wrapper


def enforce_idle_timeout(app):
    """Install the single global idle-timeout guard (see module docstring)."""
    from flask_login import logout_user, user_logged_in

    def _on_login(sender, user, **extra):
        if user is not None:
            touch_user_activity(user.id, app.config.get("APP_NAME"), throttle_seconds=0)

    app.extensions.setdefault("cm_session_hooks", {})["on_login"] = _on_login
    user_logged_in.connect(_on_login, app)

    @app.before_request
    def _cm_idle_guard():
        if request.method == "OPTIONS":
            return None

        endpoint = request.endpoint
        if not endpoint:
            return None
        if endpoint.rsplit(".", 1)[-1] in ("static", "login", "logout", "sign"):
            return None
        if endpoint in (
            _cfg("SESSION_LOGIN_ENDPOINT", "views.login"),
            _cfg("SESSION_LOGOUT_ENDPOINT", "auth.logout"),
        ):
            return None

        if not current_user.is_authenticated:
            return None

        app_name = _cfg("APP_NAME", None)
        if not app_name:
            return None

        user = current_user._get_current_object()
        now = _naive(current_utc_time())
        last = _naive(get_app_last_active(user.id, app_name))

        if last is None:
            touch_user_activity(user.id, app_name, throttle_seconds=0)
            return None

        if _enforcing() and now - last > get_user_session_timeout(user):
            logout_user()
            if _wants_json():
                return jsonify({"success": False, "error": "session_expired"}), 401
            return force_logout()

        if _is_activity_request():
            touch_user_activity(
                user.id, app_name,
                throttle_seconds=int(_cfg("SESSION_ACTIVITY_WRITE_INTERVAL", 45)),
            )
        return None


def get_current_user():
    data = get_session_from_cookie()
    return User.query.get(data["user_id"]) if data else None
