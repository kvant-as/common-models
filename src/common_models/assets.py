"""Shared front-end assets (JS/CSS) used by both enPlans and erespondentN —
served from here instead of being duplicated (and drifting) in each app's
own static/ folder. Same pattern as common_models.admin's own static files.

Each app calls ``init_assets(app)`` once during ``create_app()``, then
references files via ``url_for('cm_assets.static', filename='js/message-flash.js')``.
"""
from flask import Blueprint

assets_bp = Blueprint(
    "cm_assets", __name__,
    static_folder="static_assets",
    static_url_path="/cm-assets",
)


def init_assets(app):
    if "cm_assets" not in app.blueprints:
        app.register_blueprint(assets_bp)
