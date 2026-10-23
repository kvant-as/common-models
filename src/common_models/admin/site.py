"""Custom admin engine: declarative model registration + generic CRUD routes."""

import os
import re
from datetime import date, datetime

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template,
    request, url_for,
)
from flask_login import current_user
from sqlalchemy import String, Text, or_
from werkzeug.utils import secure_filename

from ..models import db

__all__ = ["AdminSite", "Field"]


# --------------------------------------------------------------------------- #
#  Field spec
# --------------------------------------------------------------------------- #

class Field:
    """One form field on a model's create/edit screen.

    type: str | text | email | int | float | bool | date | datetime |
          select | fk | password | file
    """

    def __init__(self, name, label=None, type="str", required=False,
                 choices=None, target=None, target_label=None, blank=True,
                 create_only=False, skip_if_blank=False, transform=None,
                 help=None, rows=5, accept=None, upload_to=None, default=None,
                 readonly=False, display=None):
        self.name = name
        self.label = label or name.replace("_", " ").capitalize()
        self.type = type
        self.required = required
        self.choices = choices or []            # list[(value, label)]
        self.target = target                    # related model for fk
        self.target_label = target_label        # attr on related model to show
        self.blank = blank                      # allow empty for fk/select
        self.create_only = create_only
        self.skip_if_blank = skip_if_blank
        self.transform = transform              # callable(value) -> value
        self.help = help
        self.rows = rows
        self.accept = accept
        self.upload_to = upload_to              # dir relative to app.root_path
        self.default = default                  # pre-filled value on the create form
        self.readonly = readonly                # shown, but not submitted/editable
        self.display = display                  # callable(obj) -> str, for readonly fields whose raw column value isn't human-friendly (e.g. a fk id)

    # -- read one value out of the submitted form --------------------------- #
    def extract(self, form, files):
        if self.readonly:
            return _MISSING
        if self.type == "bool":
            return self.name in form
        if self.type == "file":
            file = files.get(self.name)
            if not file or not file.filename:
                return _MISSING
            dest_dir = os.path.join(current_app.root_path, self.upload_to or "static/uploads")
            os.makedirs(dest_dir, exist_ok=True)
            fname = _safe_upload_name(file.filename)
            root, ext = os.path.splitext(fname)
            i = 1
            while os.path.exists(os.path.join(dest_dir, fname)):
                fname = f"{root}-{i}{ext}"
                i += 1
            file.save(os.path.join(dest_dir, fname))
            return fname                     # stored verbatim in the model column

        raw = (form.get(self.name) or "").strip()
        if raw == "":
            if self.skip_if_blank:
                return _MISSING
            return None if self.blank or not self.required else ""

        if self.type in ("int", "fk", "fk-search"):
            try:
                return int(raw)
            except ValueError:
                return None
        if self.type == "float":
            try:
                return float(raw.replace(",", "."))
            except ValueError:
                return None
        if self.type == "date":
            return _parse_dt(raw, "%Y-%m-%d")
        if self.type == "datetime":
            return _parse_dt(raw, "%Y-%m-%dT%H:%M")
        return raw

    def options(self):
        if self.type == "select":
            return list(self.choices)
        if self.type == "fk" and self.target is not None:
            pk = self.target.__mapper__.primary_key[0].name
            rows = self.target.query.all()
            rows.sort(key=lambda o: _smart_label(o).lower())
            return [(getattr(o, pk), _smart_label(o, self.target_label)) for o in rows]
        return []


_MISSING = object()


# --------------------------------------------------------------------------- #
#  Model registration
# --------------------------------------------------------------------------- #

class ModelAdmin:
    def __init__(self, model, name, group="Прочее", key=None,
                 list_display=None, list_badges=(), list_format=None,
                 search=(), order_by="-id", per_page=25,
                 can_create=True, can_edit=True, can_delete=True,
                 fields=(), readonly=False, stat_label=None, stat_count=None,
                 on_save=None, scope_query=None):
        self.model = model
        self.name = name
        self.group = group
        self.key = key or _slug(model.__name__)
        self.is_link = False    # duck-typing flag so base.html can tell a ModelAdmin from a _NavLink
        self.pk_name = model.__mapper__.primary_key[0].name
        # Каждый элемент — либо имя атрибута (колонка так и подписывается),
        # либо (ключ, подпись) — для вычисляемых колонок через list_format,
        # у которых ключ не обязан быть реальным атрибутом модели/красивой
        # подписью одновременно.
        self.list_display = [
            d if isinstance(d, (tuple, list)) else (d, d)
            for d in (list_display or ["id"])
        ]
        self.list_badges = tuple(list_badges)
        self.list_format = dict(list_format or {})
        self.search = tuple(search)
        self.order_by = order_by
        self.per_page = per_page
        self.readonly = readonly
        self.can_create = can_create and not readonly
        self.can_edit = can_edit and not readonly
        self.can_delete = can_delete and not readonly
        self.fields = list(fields)
        self.stat_label = stat_label
        self.stat_count = stat_count
        self.on_save = on_save          # callable(obj, creating) before commit
        self.scope_query = scope_query  # optional callable(query) -> query, applied to list/search/fk-search

    # -- queries ---------------------------------------------------------- #
    def base_query(self):
        q = self.model.query
        if self.scope_query:
            q = self.scope_query(q)
        col = self.order_by.lstrip("-")
        if hasattr(self.model, col):
            attr = getattr(self.model, col)
            q = q.order_by(attr.desc() if self.order_by.startswith("-") else attr)
        return q

    def search_query(self, q, term):
        if not term or not self.search:
            return q
        clauses = []
        for name in self.search:
            col = self.model.__table__.columns.get(name)
            if col is not None and isinstance(col.type, (String, Text)):
                clauses.append(getattr(self.model, name).ilike(f"%{term}%"))
        return q.filter(or_(*clauses)) if clauses else q

    def form_fields(self, creating):
        return [f for f in self.fields if not (f.create_only and not creating)]

    # -- rendering helpers --------------------------------------------------- #
    def cell(self, obj, name):
        if name in self.list_format:
            return self.list_format[name](obj)
        return _format_value(getattr(obj, name, None))

    def title(self, obj):
        return _smart_label(obj)

    def pk(self, obj):
        return getattr(obj, self.pk_name)

    def count(self):
        if self.stat_count:
            return self.stat_count()
        return self.model.query.count()


# --------------------------------------------------------------------------- #
#  Site
# --------------------------------------------------------------------------- #

_bp = Blueprint(
    "cm_admin", __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/cm-admin-static",
)


class _NavLink:
    """A plain sidebar link to a custom page (e.g. AdminSite.link(...)) —
    not backed by a registered ModelAdmin, so it has no CRUD/list route of
    its own; ``endpoint`` is resolved via url_for() when the nav renders."""

    def __init__(self, label, endpoint, group):
        self.name = label
        self.group = group
        self.endpoint = endpoint
        self.is_link = True


class AdminSite:
    def __init__(self, brand, accent="#2563eb", accent_2=None,
                 url_prefix="/admin", site_endpoint=None,
                 login_endpoint="auth.login", logout_endpoint="auth.logout"):
        self.brand = brand
        self.accent = accent
        self.accent_2 = accent_2 or accent
        self.url_prefix = url_prefix
        self.site_endpoint = site_endpoint
        self.login_endpoint = login_endpoint
        self.logout_endpoint = logout_endpoint

        self._models = {}          # key -> ModelAdmin
        self._links = []           # list of _NavLink — plain nav links not backed by a ModelAdmin
        self._dash = {
            "greeting_attr": None,
            "stats": [],
            "online_count": None,      # optional callable -> int
            "actions": [],             # list of {label, endpoint|url, method, confirm}
            "panels": [],              # list of {title, rows, empty}
        }

    # -- public API ------------------------------------------------------- #
    def register(self, model, **kw):
        ma = ModelAdmin(model, **kw)
        self._models[ma.key] = ma
        return ma

    def link(self, label, endpoint, group="Прочее"):
        """Add a plain nav link (e.g. to a custom page that isn't a
        registered model's CRUD) into the sidebar, grouped the same way as
        registered models — resolved lazily via ``url_for(endpoint)`` on
        each page load, so it's safe to call at import time."""
        self._links.append(_NavLink(label, endpoint, group))

    def dashboard(self, greeting_attr=None, stats=(), online_count=None, actions=(), panels=()):
        """Configure the admin home page: a greeting, a row of count cards for
        the given registered model keys, an optional live "online now" number
        from ``online_count()``, an optional list of ``actions`` rendered as
        buttons that call their endpoint via fetch and show the JSON
        ``message`` — no page navigation. Each is either::

            {"label", "endpoint"|"url", "method"="post", "confirm"=None}

        (plain POST, no body) or, with ``"type": "upload"``, a file-picker
        button that uploads the chosen file as ``multipart/form-data``::

            {"label", "endpoint"|"url", "type": "upload",
             "field"="file", "accept"=None, "confirm"=None}

        ``panels`` add one or more "needs attention" lists above the actions —
        e.g. open support chats. Each is::

            {"title": "...", "rows": callable_or_list, "empty": "...",
             "more_endpoint"=None, "more_url"=None, "more_label"="Показать все"}

        ``more_endpoint`` (resolved via ``url_for`` — same convention as
        ``actions``) or ``more_url`` (optional) renders a link next to the
        title — e.g. to a dedicated full list page when ``rows`` only shows
        a capped preview.

        ``rows`` is called fresh on every dashboard load (so it can query the
        DB) and must return dicts shaped
        ``{"title", "subtitle"="", "meta"="", "url"}``.
        """
        self._dash.update(
            actions=[dict(a) for a in actions],
            greeting_attr=greeting_attr,
            stats=list(stats),
            online_count=online_count,
            panels=[dict(p) for p in panels],
        )

    def init_app(self, app):
        app.extensions["cm_admin"] = self
        if "cm_admin" not in app.blueprints:
            app.register_blueprint(_bp, url_prefix=self.url_prefix)

    # -- internals ------------------------------------------------------- #
    def get(self, key):
        ma = self._models.get(key)
        if ma is None:
            abort(404)
        return ma

    def groups(self):
        out = {}
        for ma in self._models.values():
            out.setdefault(ma.group, []).append(ma)
        for link in self._links:
            out.setdefault(link.group, []).append(link)
        return out

    def nav_context(self):
        return {"site": self, "groups": self.groups()}


def _site():
    site = current_app.extensions.get("cm_admin")
    if site is None:
        abort(404)
    return site


# --------------------------------------------------------------------------- #
#  Auth
# --------------------------------------------------------------------------- #

@_bp.before_request
def _guard():
    if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
        site = _site()
        flash("Требуется вход администратора", "error")
        return redirect(url_for(site.login_endpoint))


# --------------------------------------------------------------------------- #
#  Routes
# --------------------------------------------------------------------------- #

@_bp.route("/")
def dashboard():
    site = _site()
    dash = site._dash
    cards = []
    for key in dash["stats"]:
        ma = site._models.get(key)
        if ma:
            cards.append({"label": ma.stat_label or ma.name, "value": ma.count(), "key": key})

    online = None
    fn = dash.get("online_count")
    if callable(fn):
        try:
            online = int(fn())
        except Exception:                              # noqa: BLE001
            online = None

    greeting = None
    if dash["greeting_attr"]:
        greeting = getattr(current_user, dash["greeting_attr"], None)
    greeting = greeting or getattr(current_user, "first_name", None) or getattr(current_user, "email", "")

    actions = []
    for a in dash.get("actions", []):
        try:
            url = a.get("url") or url_for(a["endpoint"])
        except Exception:                              # noqa: BLE001
            continue
        actions.append({
            "label": a.get("label", "Действие"),
            "url": url,
            "method": (a.get("method") or "post").upper(),
            "confirm": a.get("confirm"),
            "type": a.get("type", "click"),      # "click" | "upload"
            "field": a.get("field", "file"),     # upload: form-data field name
            "accept": a.get("accept"),           # upload: <input accept="...">
        })

    panels = []
    for p in dash.get("panels", []):
        rows_src = p.get("rows")
        try:
            rows = rows_src() if callable(rows_src) else list(rows_src or [])
        except Exception:                              # noqa: BLE001
            rows = []

        more_url = p.get("more_url")
        if not more_url and p.get("more_endpoint"):
            try:
                more_url = url_for(p["more_endpoint"])
            except Exception:                          # noqa: BLE001
                more_url = None

        panels.append({
            "title": p.get("title", ""),
            "rows": rows,
            "empty": p.get("empty", "Пусто"),
            "more_url": more_url,
            "more_label": p.get("more_label"),
        })

    return render_template(
        "cm_admin/dashboard.html",
        cards=cards, greeting=greeting, online=online, actions=actions, panels=panels,
        **site.nav_context(),
    )


@_bp.route("/_fk-search")
def fk_search_view():
    """Backs the searchable combobox for ``type="fk-search"`` fields — reuses
    the target model's own registered search config (``ModelAdmin.search``)
    instead of a separate one, so e.g. the Organization picker on the User
    form searches the same fields (full_name/okpo/ynp) as the Organization
    list page itself."""
    from flask import jsonify

    site = _site()
    target_key = request.args.get("target", "")
    term = request.args.get("q", "").strip()
    ma = site._models.get(target_key)
    if ma is None:
        return jsonify([])

    q = ma.search_query(ma.base_query(), term)
    rows = q.limit(20).all()
    return jsonify([{"id": ma.pk(o), "label": ma.title(o)} for o in rows])


@_bp.route("/<key>/")
def list_view(key):
    site = _site()
    ma = site.get(key)
    term = request.args.get("q", "").strip()
    page = max(1, request.args.get("page", 1, type=int))

    q = ma.search_query(ma.base_query(), term)
    total = q.count()
    rows = q.offset((page - 1) * ma.per_page).limit(ma.per_page).all()
    pages = max(1, (total + ma.per_page - 1) // ma.per_page)

    return render_template(
        "cm_admin/list.html",
        ma=ma, rows=rows, term=term, page=page, pages=pages, total=total,
        **site.nav_context(),
    )


@_bp.route("/<key>/new", methods=["GET", "POST"])
def create_view(key):
    site = _site()
    ma = site.get(key)
    if not ma.can_create:
        abort(403)
    return _edit(site, ma, obj=ma.model(), creating=True)


@_bp.route("/<key>/<int:pk>/edit", methods=["GET", "POST"])
def edit_view(key, pk):
    site = _site()
    ma = site.get(key)
    obj = db.session.get(ma.model, pk) or abort(404)
    if request.method == "POST" and not ma.can_edit:
        abort(403)
    return _edit(site, ma, obj=obj, creating=False)


@_bp.route("/<key>/<int:pk>/delete", methods=["POST"])
def delete_view(key, pk):
    site = _site()
    ma = site.get(key)
    if not ma.can_delete:
        abort(403)
    obj = db.session.get(ma.model, pk) or abort(404)
    try:
        db.session.delete(obj)
        db.session.commit()
        flash(f"«{ma.title(obj)}» удалено", "success")
    except Exception as exc:                       # noqa: BLE001
        db.session.rollback()
        flash(f"Не удалось удалить: {exc}", "error")
    return redirect(url_for("cm_admin.list_view", key=key))


def _edit(site, ma, obj, creating):
    fields = ma.form_fields(creating)
    errors = {}

    if request.method == "POST":
        for f in fields:
            value = f.extract(request.form, request.files)
            if value is _MISSING:
                continue
            if f.required and (value in (None, "")):
                errors[f.name] = "Обязательное поле"
                continue
            if f.transform and value not in (None, ""):
                value = f.transform(value)
            setattr(obj, f.name, value)

        if not errors:
            try:
                if ma.on_save:
                    ma.on_save(obj, creating)
                if creating:
                    db.session.add(obj)
                db.session.commit()
                flash("Сохранено", "success")
                return redirect(url_for("cm_admin.list_view", key=ma.key))
            except Exception as exc:                # noqa: BLE001
                db.session.rollback()
                errors["__all__"] = str(exc)

    def _fv_value(f):
        v = getattr(obj, f.name, None)
        if v is None and creating and f.default is not None:
            return f.default
        return v

    def _fk_target_key(f):
        if f.target is None:
            return None
        for ma2 in site._models.values():
            if ma2.model is f.target:
                return ma2.key
        return None

    def _fk_current_label(f, value):
        if f.target is None or value in (None, ""):
            return ""
        related = db.session.get(f.target, value)
        return _smart_label(related, f.target_label) if related else ""

    field_views = []
    for f in fields:
        value = f.display(obj) if (f.readonly and f.display) else _fv_value(f)
        field_views.append({
            "spec": f,
            "value": value,
            "options": f.options(),
            "error": errors.get(f.name),
            "target_key": _fk_target_key(f) if f.type == "fk-search" else None,
            "current_label": _fk_current_label(f, value) if f.type == "fk-search" else None,
        })

    return render_template(
        "cm_admin/form.html",
        ma=ma, obj=obj, creating=creating,
        field_views=field_views, form_error=errors.get("__all__"),
        **site.nav_context(),
    )


# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #

def _slug(name):
    out = []
    for i, ch in enumerate(name):
        if ch == "_":
            out.append("-")
            continue
        if ch.isupper() and i and name[i - 1] not in "_-" and not name[i - 1].isupper():
            out.append("-")
        out.append(ch.lower())
    return "".join(out).strip("-")


_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _translit(text):
    out = []
    for ch in text or "":
        rep = _TRANSLIT.get(ch.lower())
        if rep is None:
            out.append(ch)
        elif ch.isupper() and rep:
            out.append(rep[0].upper() + rep[1:])
        else:
            out.append(rep)
    return "".join(out)


def _safe_upload_name(original):
    """ASCII, filesystem-safe file name derived from ``original`` (transliterating
    Cyrillic), always keeping a sane extension."""
    original = original or "file"
    stem, ext = os.path.splitext(original)
    ext = "." + re.sub(r"[^A-Za-z0-9]", "", ext).lower()[:12] if ext else ""
    stem = secure_filename(_translit(stem)).strip("._-")[:80]
    if not stem:
        stem = "file-" + os.urandom(4).hex()
    return stem + ext


def _parse_dt(raw, fmt):
    try:
        return datetime.strptime(raw, fmt)
    except ValueError:
        return None


def _format_value(val):
    if val is None or val == "":
        return "—"
    if isinstance(val, bool):
        return "✓" if val else "—"
    if isinstance(val, datetime):
        return val.strftime("%d.%m.%Y %H:%M")
    if isinstance(val, date):
        return val.strftime("%d.%m.%Y")
    if isinstance(val, db.Model):
        return _smart_label(val)
    text = str(val)
    return text if len(text) <= 80 else text[:77] + "…"


_LABEL_ATTRS = (
    "full_name", "name", "title", "fio", "label", "email", "code",
    "NameProduct", "NameUnit", "CodeUnit", "CodeProduct",
)


def _smart_label(obj, prefer=None):
    if obj is None:
        return "—"
    for attr in ((prefer,) if prefer else ()) + _LABEL_ATTRS:
        if attr and getattr(obj, attr, None):
            return str(getattr(obj, attr))
    try:
        pk = getattr(obj, obj.__mapper__.primary_key[0].name)
    except Exception:                                  # noqa: BLE001
        pk = "?"
    return f"{obj.__class__.__name__} #{pk}"
