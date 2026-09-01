"""Per-app user activity tracking.

Call :func:`touch_user_activity` on authenticated requests (e.g. from the
``session_required`` guard) to record that ``user_id`` was active in ``app``
right now.  The first call for a pair also stamps ``first_seen``.  This is the
single source of truth for "when was the user last here" — there is no global
``user.last_active`` column any more, activity is stored per application in
:class:`UserAppActivity`.

Writes are throttled: if the stored ``last_active`` is younger than
``throttle_seconds`` the call is a cheap no-op, so it is safe to invoke on
every request (pass ``throttle_seconds=0`` to force a write, e.g. on login).
Any database error is swallowed and logged — activity bookkeeping must never
break the request it is attached to.
"""

from datetime import timedelta

from .models import db, UserAppActivity
from .timeutils import current_utc_time
from .logs import get_logger

__all__ = ["touch_user_activity", "get_app_last_active", "count_online"]


def touch_user_activity(user_id, app, throttle_seconds=60):
    """Upsert ``(user_id, app)`` activity in :class:`UserAppActivity`.

    Returns ``True`` if a write happened, ``False`` if throttled or on error.
    """
    if not user_id or not app:
        return False

    now = current_utc_time()
    try:
        row = (
            db.session.query(UserAppActivity)
            .filter_by(user_id=user_id, app=app)
            .one_or_none()
        )

        if row is not None and row.last_active and \
                (now - row.last_active) < timedelta(seconds=throttle_seconds):
            return False

        if row is None:
            db.session.add(
                UserAppActivity(user_id=user_id, app=app, first_seen=now, last_active=now)
            )
        else:
            row.last_active = now

        db.session.commit()
        return True

    except Exception:
        db.session.rollback()
        get_logger().warning("touch_user_activity failed", exc_info=True)
        return False


def get_app_last_active(user_id, app):
    """Return ``UserAppActivity.last_active`` for ``(user_id, app)`` or ``None``."""
    if not user_id or not app:
        return None
    try:
        row = (
            db.session.query(UserAppActivity.last_active)
            .filter_by(user_id=user_id, app=app)
            .one_or_none()
        )
        return row[0] if row else None
    except Exception:
        get_logger().warning("get_app_last_active failed", exc_info=True)
        return None


def count_online(app, within_minutes=5):
    """Distinct users active in ``app`` within the last ``within_minutes``."""
    if not app:
        return 0
    try:
        since = current_utc_time() - timedelta(minutes=within_minutes)
        return (
            db.session.query(UserAppActivity.user_id)
            .filter(UserAppActivity.app == app, UserAppActivity.last_active >= since)
            .distinct()
            .count()
        )
    except Exception:
        get_logger().warning("count_online failed", exc_info=True)
        return 0
