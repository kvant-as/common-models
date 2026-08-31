"""Shared idle-session tracking for kvant-as Flask apps.

A short-lived JWT cookie carries ``last_active`` / ``created_at`` claims; the
:func:`session_required` guard refreshes it on every request and logs the user
out once the idle timeout is exceeded.  Persistent activity is written to the
``user_app_activity`` table via :func:`common_models.touch_user_activity`.

Behaviour is tuned per app through ``app.config``:

=============================  =========================================  ==============================
Key                            Default                                    Meaning
=============================  =========================================  ==============================
``SESSION_TOKEN_COOKIE``       ``session_token``                          Cookie name for the idle token.
``SESSION_TIMEOUT_PRIVILEGED`` ``timedelta(hours=9)``                     Idle timeout for privileged users.
``SESSION_TIMEOUT_DEFAULT``    ``timedelta(minutes=60)``                  Idle timeout for everyone else.
``SESSION_PRIVILEGED_ATTRS``   ``('is_admin', 'is_auditor',
                                  'is_approver', 'is_reader')``           User flags granting the long timeout.
``SESSION_LOGIN_ENDPOINT``     ``views.login``                            Endpoint to redirect to on logout.
``SESSION_DEFAULT_REDIRECT``   ``views.profile``                          Default target of ``create_login_response``.
``SESSION_ENFORCE_IN_DEBUG``   ``False``                                 Keep enforcing the timeout when ``app.debug``.
``APP_NAME``                   --                                        Passed to ``touch_user_activity``.
=============================  =========================================  ==============================
"""

import uuid
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import request, redirect, url_for, flash, make_response, current_app
from flask_login import current_user
from user_agents import parse

from .models import db, User
from .timeutils import current_utc_time
from .activity import touch_user_activity

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
    "get_current_user",
    "clear_session_cookie",
]

JWT_ALGORITHM = "HS256"
SESSION_DURATION = timedelta(days=7)  # JWT lifetime, distinct from the idle timeout

_DEFAULT_PRIVILEGED_ATTRS = ("is_admin", "is_auditor", "is_approver", "is_reader")


def _cfg(key, default):
    return current_app.config.get(key, default)


def _cookie_name():
    return _cfg("SESSION_TOKEN_COOKIE", "session_token")


def get_user_session_timeout(user):
    attrs = _cfg("SESSION_PRIVILEGED_ATTRS", _DEFAULT_PRIVILEGED_ATTRS)
    if any(getattr(user, attr, False) for attr in attrs):
        return _cfg("SESSION_TIMEOUT_PRIVILEGED", timedelta(hours=9))
    return _cfg("SESSION_TIMEOUT_DEFAULT", timedelta(minutes=60))


def _naive(dt):
    if dt is not None and getattr(dt, "tzinfo", None) is not None:
        return dt.replace(tzinfo=None)
    return dt


def get_session_time_left():
    """Seconds left before idle logout, plus the total timeout (both ints),
    or ``None`` when there is no valid session. Used by the header timer."""
    session_data = get_session_from_cookie()
    if not session_data:
        return None

    user = User.query.get(session_data["user_id"])
    if not user:
        return None

    last_active = _naive(datetime.fromisoformat(session_data["last_active"]))
    current_time = _naive(current_utc_time())

    session_timeout = get_user_session_timeout(user)
    seconds_left = (session_timeout - (current_time - last_active)).total_seconds()
    return max(0, int(seconds_left)), int(session_timeout.total_seconds())


def create_session_token(user):
    now = current_utc_time()
    payload = {
        "user_id": user.id,
        "email": user.email,
        "full_name": f"{user.last_name or ''} {user.first_name or ''} {user.patronymic_name or ''}".strip(),
        "is_admin": bool(getattr(user, "is_admin", False)),
        "is_auditor": bool(getattr(user, "is_auditor", False)),
        "session_id": str(uuid.uuid4()),
        "created_at": now.isoformat(),
        "last_active": now.isoformat(),
        "exp": (now + SESSION_DURATION).timestamp(),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=JWT_ALGORITHM)


def set_session_cookie(response, token):
    response.set_cookie(
        _cookie_name(),
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=False,
        samesite="Lax",
        path="/",
    )
    return response


def create_login_response(user, redirect_endpoint=None):
    endpoint = redirect_endpoint or _cfg("SESSION_DEFAULT_REDIRECT", "views.profile")
    token = create_session_token(user)
    response = make_response(redirect(url_for(endpoint)))
    return set_session_cookie(response, token)


def verify_session_token(token):
    try:
        return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        current_app.logger.debug("Session token expired")
        return None
    except jwt.InvalidTokenError as e:
        current_app.logger.debug(f"Invalid session token: {e}")
        return None


def get_session_from_cookie():
    token = request.cookies.get(_cookie_name())
    if not token:
        return None
    return verify_session_token(token)


def update_session_activity(token):
    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        payload["last_active"] = current_utc_time().isoformat()
        return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=JWT_ALGORITHM)
    except jwt.InvalidTokenError:
        return None


def describe_device(ua_string):
    try:
        ua = parse(ua_string or "")
        browser = ua.browser.family or "Браузер"
        os_name = ua.os.family or ""
        return f"{browser} · {os_name}".strip(" ·") or "Неизвестное устройство"
    except Exception:
        return "Неизвестное устройство"


def build_session_info(user, payload=None):
    """Session data for the 'Сессии' profile section / session-info endpoint."""
    timeout = get_user_session_timeout(user)
    now = current_utc_time()

    last_active = now
    created_at = now
    device = describe_device(request.headers.get("User-Agent", ""))

    if payload:
        try:
            last_active = datetime.fromisoformat(payload.get("last_active"))
        except (TypeError, ValueError):
            pass
        try:
            created_at = datetime.fromisoformat(payload.get("created_at"))
        except (TypeError, ValueError):
            pass

    if user.is_admin:
        role_label = "Администратор"
    elif getattr(user, "is_auditor", False):
        role_label = "Аудитор"
    elif getattr(user, "is_approver", False):
        role_label = "Утверждающий"
    elif getattr(user, "is_reader", False):
        role_label = "Читатель"
    else:
        role_label = "Респондент"

    return {
        "role_label": role_label,
        "timeout_minutes": int(timeout.total_seconds() // 60),
        "created_at": created_at.isoformat(),
        "last_active": last_active.isoformat(),
        "expires_at": (last_active + timeout).isoformat(),
        "server_time": now.isoformat(),
        "device": device,
        "ip": request.remote_addr or "",
    }


def get_or_refresh_session(user):
    """Read the idle token for this request, refreshing its ``last_active``,
    or mint a fresh one if it is missing/expired. Returns ``(token, payload)``."""
    token = request.cookies.get(_cookie_name())
    payload = verify_session_token(token) if token else None

    if payload:
        token = update_session_activity(token) or token
    else:
        token = create_session_token(user)

    return token, verify_session_token(token)


def force_logout():
    login_endpoint = _cfg("SESSION_LOGIN_ENDPOINT", "views.login")
    response = make_response(redirect(url_for(login_endpoint)))
    response.delete_cookie(_cookie_name(), path="/")
    flash("Сессия недействительна или истекла. Пожалуйста, войдите снова", "error")
    return response


def session_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        debug = current_app.debug
        enforce_raw = _cfg("SESSION_ENFORCE_IN_DEBUG", False)
        enforce_in_debug = (
            enforce_raw if isinstance(enforce_raw, bool)
            else str(enforce_raw).lower() in {"1", "true", "yes", "on"}
        )

        if debug and not enforce_in_debug:
            return view_func(*args, **kwargs)

        token = request.cookies.get(_cookie_name())
        session_data = verify_session_token(token) if token else None

        if not session_data:
            if current_user.is_authenticated:
                # Flask-Login session is still valid but our idle token is
                # missing/expired (e.g. predates this mechanism). Self-heal
                # instead of a disruptive logout.
                token = create_session_token(current_user._get_current_object())
                session_data = verify_session_token(token)
            elif debug:
                return view_func(*args, **kwargs)
            else:
                return force_logout()

        user = User.query.get(session_data["user_id"])
        if not user:
            if debug:
                return view_func(*args, **kwargs)
            return force_logout()

        last_active = _naive(datetime.fromisoformat(session_data["last_active"]))
        current_time = _naive(current_utc_time())
        session_timeout = get_user_session_timeout(user)

        if current_time - last_active > session_timeout:
            return force_logout()

        touch_user_activity(user.id, _cfg("APP_NAME", None))

        new_token = update_session_activity(token)
        response = view_func(*args, **kwargs)

        if isinstance(response, str):
            response = make_response(response)

        if new_token and new_token != token:
            response = set_session_cookie(response, new_token)

        return response

    return wrapper


def get_current_user():
    session_data = get_session_from_cookie()
    if session_data:
        return User.query.get(session_data["user_id"])
    return None


def clear_session_cookie(response):
    response.delete_cookie(_cookie_name(), path="/")
    return response
