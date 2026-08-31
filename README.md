# common-models

Shared code for the kvant-as Flask apps (`enPlans`, `erespondentN`):

| Module | What it provides |
| --- | --- |
| `common_models` | Flask-SQLAlchemy `db` + all ORM models, re-exported at package root |
| `common_models.timeutils` | quarter / report-year helpers, `current_utc_time` |
| `common_models.logs` | `setup_logging(app)`, `get_logger()`, `log_with_extra()` |
| `common_models.mailer` | rate-limited SMTP send queue (`get_email_queue()`) |
| `common_models.activity` | `touch_user_activity(user_id, app)` — per-app first-seen / last-active |
| `common_models.sessions` | idle-session JWT cookie + `session_required` guard, config-driven |
| `common_models/migrations/` | the single Alembic history for the shared database |
| `common_models.admin` | custom admin engine (`AdminSite`, `Field`); each app registers its own models |
| `common_models/templates/` | shared Jinja templates (`macros/svg_icons.html`) |

## Install (editable, for local development)

Check the repo out next to the apps and install it into each app's venv:

```
d:/work/eres/
├─ common-models/
├─ enPlans/
└─ erespondentN/
```

```
pip install -e ../common-models
```

Consumers resolve the bundled templates with
`importlib.resources.files("common_models") / "templates"`.

## Environment variables

### Logging (`common_models.logs`)

| Key | Default | Meaning |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Root level: DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `LOG_JSON` | `false` | Emit console logs as JSON instead of coloured text |
| `LOG_STATIC_REQUESTS` | `false` | Keep `GET /static/` lines from werkzeug |
| `LOG_TO_FILE` | `false` | Also write JSON logs to a rotating file |
| `LOG_DIR` | `logs` | Folder for the log file, relative to the project root |
| `LOG_FILE` | `<app>.json` | File name inside `LOG_DIR` |

When `LOG_TO_FILE` is on, a `logs/` folder is created in that app's project
root and logs are written to `logs/<LOG_FILE>` as JSON
(`RotatingFileHandler`, 5 MB × 5 backups).

### Mail (`common_models.mailer`)

| Key | Default | Meaning |
| --- | --- | --- |
| `SMTP_HOST` | — | SMTP server host (required) |
| `EMAILS_PER_MINUTE` | `6` | Per-account send rate |
| `EMAILS_DAILY_LIMIT` | `10000` | Per-account daily cap |
| `ACC_<n>_EMAIL` / `ACC_<n>_PASS` | — | Sender accounts, numbered from 1 |

Each app keeps its own `website/email.py` (subject map) and
`website/email_html.py` (branded HTML) and pushes ready messages in via
`get_email_queue().add(to, subject, html, email_type)`.

## User activity per app

`user.begin_time` is the global account-creation date (auto-stamped by the
column default). Per-app presence lives in the `user_app_activity` table
(`UserAppActivity` model): one row per `(user_id, app)` with `first_seen` and
`last_active`.

Each app sets `APP_NAME` in its config (`enplans` / `erespondentn`) and calls
`touch_user_activity(user.id, current_app.config["APP_NAME"])` from the
`session_required` guard. Writes are throttled (default 60 s) and errors are
swallowed, so it is safe on every request.

```python
# "last active anywhere" for a user
db.session.query(db.func.max(UserAppActivity.last_active)).filter_by(user_id=uid).scalar()

# per-app breakdown
UserAppActivity.query.filter_by(user_id=uid).all()
```

The table is created by `db.create_all()` on startup; no Alembic migration is
needed.

## Sessions (`common_models.sessions`)

Idle-session tracking (short-lived JWT cookie + `session_required` decorator +
`build_session_info` / `get_session_time_left` / `create_login_response` …) is
shared. `session_required` refreshes the cookie, enforces the idle timeout, and
calls `touch_user_activity` on each pass. Each app keeps a thin
`website/sessions.py` that re-exports this module.

Per-app behaviour comes from `app.config`:

| Key | Default | |
| --- | --- | --- |
| `SESSION_TOKEN_COOKIE` | `session_token` | idle-token cookie name |
| `SESSION_TIMEOUT_PRIVILEGED` | `timedelta(hours=9)` | timeout for privileged users |
| `SESSION_TIMEOUT_DEFAULT` | `timedelta(minutes=60)` | timeout for everyone else |
| `SESSION_PRIVILEGED_ATTRS` | `('is_admin','is_auditor','is_approver','is_reader')` | flags granting the long timeout |
| `SESSION_LOGIN_ENDPOINT` | `views.login` | logout redirect target |
| `SESSION_DEFAULT_REDIRECT` | `views.profile` | default target of `create_login_response` |
| `SESSION_ENFORCE_IN_DEBUG` | `False` | keep enforcing the timeout when `app.debug` |

`setup_logging` also prints an init banner with `APP_NAME` and the
password-masked `SQLALCHEMY_DATABASE_URI`.

## Database migrations

Both apps share one database, so there is one Alembic history and it lives here,
in `common_models/migrations/`. Each app points Flask-Migrate at it:

```python
from importlib.resources import files
migrate.init_app(app, db,
                 directory=str(files("common_models") / "migrations"),
                 render_as_batch=True)
```

Neither app calls `db.create_all()` any more — the schema is created and
evolved only through migrations.

```
# bootstrap a fresh database (from either app dir, with its venv + .env):
FLASK_APP=main.py flask db upgrade

# after changing models in common_models (run from ONE app only):
FLASK_APP=main.py flask db migrate -m "what changed"
FLASK_APP=main.py flask db upgrade
```

`flask db migrate` writes the new revision into this package, so keep
`common-models` installed as `pip install -e` while developing. Do not run
`flask db init` — the scaffold already exists.

If the shared database was previously built by `db.create_all()` (no
`alembic_version` table), stamp it once before the first upgrade:
`flask db stamp 9c35ff2f0fb4` (the pre-existing baseline), then
`flask db upgrade`.

## Admin (`common_models.admin`)

A small custom admin (blueprint + generic list/create/edit/delete + Jinja
templates + one CSS, light theme, accent colour per app) replaces Flask-Admin.
The engine lives here; **each app owns its own registry** in `website/admin.py`:

```python
from common_models.admin import AdminSite, Field as F

site = AdminSite(brand="EnPlans", accent="#00798f", accent_2="#009bb6",
                 site_endpoint="views.begin_page",
                 login_endpoint="auth.login", logout_endpoint="auth.logout")

site.register(User, name="Пользователи", group="Основные",
              list_display=["id", "email", "fio", "organization", "last_active"],
              list_badges=["is_admin", "is_auditor"],
              search=["email", "fio"],
              fields=[
                  F("email", "Email", type="email", required=True),
                  F("organization_id", "Организация", type="fk",
                    target=Organization, target_label="full_name"),
                  F("password", "Пароль", type="password", skip_if_blank=True,
                    transform=generate_password_hash),
              ])

site.dashboard(greeting_attr="first_name", stats=["news", "plan", "user"],
               recent="plan-ticket", recent_display=["begin_time", "note"])
```

Then in `create_app`: `from .admin import init_admin; init_admin(app)` (mounts
at `/admin`, guarded by `current_user.is_admin`).

`Field` types: `str · text · email · int · float · bool · date · datetime ·
select · fk · password · file`. `readonly=True` on a model disables
create/edit/delete (used for `UserAppActivity`).
