"""Small shared form helpers used by both apps' auth pages.

Currently: a password-strength meter. Wire it up in ``create_app``::

    from common_models.forms_ui import init_forms_ui
    init_forms_ui(app)

then on the registration page drop ``{{ cm_forms_assets() }}`` once and, after
a password ``<input>``::

    <div data-cm-pwmeter="#id-of-password-input" data-min="5"></div>

The script also sets ``minlength`` on the target input; keep a server-side
length check as well, HTML validation can be bypassed.
"""

from flask import Blueprint, url_for
from markupsafe import Markup

__all__ = ["init_forms_ui", "MIN_PASSWORD_LENGTH"]

MIN_PASSWORD_LENGTH = 5

_bp = Blueprint(
    "cm_forms", __name__,
    static_folder="forms_ui_assets/static",
    static_url_path="/cm-forms-static",
)


def init_forms_ui(app, url_prefix="/_forms"):
    if "cm_forms" not in app.blueprints:
        app.register_blueprint(_bp, url_prefix=url_prefix)

    @app.context_processor
    def _inject():
        def cm_forms_assets():
            return Markup(
                '<link rel="stylesheet" href="{css}">'
                '<script src="{js}" defer></script>'.format(
                    css=url_for("cm_forms.static", filename="pwmeter.css"),
                    js=url_for("cm_forms.static", filename="pwmeter.js"),
                )
            )

        return {"cm_forms_assets": cm_forms_assets, "cm_min_password_length": MIN_PASSWORD_LENGTH}
