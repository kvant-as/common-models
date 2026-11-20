"""Доступ внешних виджетов (например, Scriptable на телефоне администратора)
к служебным счётчикам приложения — по секретному токену, без сессии.

Токен задаётся переменной окружения ``ADMIN_WIDGET_TOKEN`` (в ``.env`` на
сервере) и передаётся в заголовке ``Authorization: Bearer <токен>``. Пока
переменная не задана, такие маршруты выключены.
"""

import hmac
import os

from flask import current_app, request

TOKEN_ENV = 'ADMIN_WIDGET_TOKEN'
MIN_TOKEN_LENGTH = 24


def widget_token_status():
    """``None`` — токен на сервере не задан (маршрут выключен), ``False`` —
    токен не передан или неверный, ``True`` — доступ разрешён."""
    expected = (current_app.config.get(TOKEN_ENV) or os.environ.get(TOKEN_ENV) or '').strip()
    if len(expected) < MIN_TOKEN_LENGTH:
        return None
    header = request.headers.get('Authorization', '')
    supplied = header[7:].strip() if header[:7].lower() == 'bearer ' else ''
    return hmac.compare_digest(supplied.encode('utf-8'), expected.encode('utf-8'))
