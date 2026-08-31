"""Per-app user activity tracking.

Call :func:`touch_user_activity` on authenticated requests (e.g. from the
``session_required`` guard) to record that ``user_id`` was active in ``app``
right now.  The first call for a pair also stamps ``first_seen``.

Each call also refreshes the global ``user.last_active`` column, so this is the
single write path for "user was here" — callers no longer touch ``user``
directly.

Writes are throttled: if the stored ``last_active`` is younger than
``throttle_seconds`` the call is a cheap no-op, so it is safe to invoke on
every request.  Any database error is swallowed and logged — activity
bookkeeping must never break the request it is attached to.
"""

from datetime import timedelta

from .models import db, User, UserAppActivity
from .timeutils import current_utc_time
from .logs import get_logger

__all__ = ["touch_user_activity"]


def touch_user_activity(user_id, app, throttle_seconds=60):
    """Upsert ``(user_id, app)`` activity and bump ``user.last_active``.

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

        db.session.query(User).filter_by(id=user_id).update(
            {User.last_active: now}, synchronize_session=False
        )
        db.session.commit()
        return True

    except Exception:
        db.session.rollback()
        get_logger().warning("touch_user_activity failed", exc_info=True)
        return False
