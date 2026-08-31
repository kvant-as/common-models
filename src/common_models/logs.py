"""Shared logging setup for kvant-as Flask apps.

Call :func:`setup_logging` once from ``create_app``.  Configuration is read from
``app.config`` (populate it from environment variables in each app):

======================  =======  ====================================================
Key                     Default  Meaning
======================  =======  ====================================================
``LOG_LEVEL``           INFO     Root log level (DEBUG/INFO/WARNING/ERROR/CRITICAL).
``LOG_JSON``            False    Emit console logs as JSON instead of coloured text.
``LOG_STATIC_REQUESTS`` False    Keep ``GET /static/`` lines from werkzeug.
``LOG_TO_FILE``         False    Also write JSON logs to a file on disk.
``LOG_DIR``             logs     Folder for the log file, relative to the project root.
``LOG_FILE``            <name>   File name inside ``LOG_DIR`` (defaults to ``<app>.json``).
======================  =======  ====================================================
"""

import sys
import json
import logging
import traceback
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

__all__ = [
    "setup_logging",
    "get_logger",
    "log_with_extra",
    "mask_db_url",
    "JSONFormatter",
    "ColoredFormatter",
    "WerkzeugFilter",
]

_FILE_MAX_BYTES = 5 * 1024 * 1024
_FILE_BACKUP_COUNT = 5


def _as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def mask_db_url(url):
    """Hide the password in a SQLAlchemy/DB URL for safe logging."""
    if not url:
        return "<not set>"
    try:
        from sqlalchemy.engine import make_url

        u = make_url(url)
        if u.password:
            u = u.set(password="***")
        return u.render_as_string(hide_password=False)
    except Exception:
        import re

        return re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:***@", str(url))


class WerkzeugFilter(logging.Filter):
    """Drop noisy ``GET /static/`` access-log lines."""

    def filter(self, record):
        return not (record.name == "werkzeug" and "GET /static/" in record.getMessage())


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "file": record.filename,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m",
    }

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        log_line = (
            f"{timestamp} | {color}{record.levelname:<8}{reset} | {record.name} | "
            f"{record.filename}:{record.lineno} | {record.getMessage()}"
        )

        if record.exc_info:
            log_line += f"\n{''.join(traceback.format_exception(*record.exc_info))}"

        return log_line


_app_logger = None


def get_logger():
    """Return the active application logger.

    Works both inside an application context (returns ``current_app.logger``)
    and outside one (returns a module-level logger with a console handler), so
    helper modules can log at import time or from background threads.
    """
    global _app_logger
    if _app_logger is not None:
        return _app_logger

    try:
        from flask import current_app

        _app_logger = current_app.logger
        return _app_logger
    except Exception:
        pass

    fallback = logging.getLogger("app")
    if not fallback.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredFormatter())
        fallback.addHandler(handler)
        fallback.setLevel(logging.DEBUG)
    return fallback


def _resolve_log_path(app):
    log_dir = app.config.get("LOG_DIR") or "logs"
    log_file = app.config.get("LOG_FILE") or f"{app.name.split('.')[0]}.json"

    directory = Path(log_dir)
    if not directory.is_absolute():
        # project root == parent of the package folder (``website/``)
        directory = Path(app.root_path).parent / directory

    directory.mkdir(parents=True, exist_ok=True)
    return directory / log_file


def setup_logging(app):
    """Configure root + Flask logging from ``app.config``. Idempotent."""
    global _app_logger

    log_level = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    log_static = _as_bool(app.config.get("LOG_STATIC_REQUESTS"), False)
    use_json = _as_bool(app.config.get("LOG_JSON"), False)
    log_to_file = _as_bool(app.config.get("LOG_TO_FILE"), False)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter() if use_json else ColoredFormatter())
    console_handler.setLevel(numeric_level)
    if not log_static:
        console_handler.addFilter(WerkzeugFilter())
    root_logger.addHandler(console_handler)

    file_path = None
    if log_to_file:
        file_path = _resolve_log_path(app)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=_FILE_MAX_BYTES,
            backupCount=_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(numeric_level)
        if not log_static:
            file_handler.addFilter(WerkzeugFilter())
        root_logger.addHandler(file_handler)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    app.logger.handlers.clear()
    app.logger.setLevel(numeric_level)
    app.logger.propagate = True
    _app_logger = app.logger

    db_url = mask_db_url(app.config.get("SQLALCHEMY_DATABASE_URI"))

    app.logger.info("=" * 60)
    app.logger.info(f"App: {app.config.get('APP_NAME', app.name)}")
    app.logger.info(f"Launch time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    app.logger.info(f"Database initialised: {db_url}")
    app.logger.info(f"Logging level: {log_level}")
    app.logger.info(f"JSON console: {use_json}")
    app.logger.info(f"Log static requests: {log_static}")
    app.logger.info(f"Log to file: {log_to_file}" + (f" ({file_path})" if file_path else ""))
    app.logger.info("=" * 60)


def log_with_extra(logger, level, message, **extra_fields):
    """Log ``message`` while attaching structured ``extra_fields`` (JSON output)."""
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra={"extra_data": extra_fields})
