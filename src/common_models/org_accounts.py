"""Ячейка «Пользователи» для списка организаций в админках обоих приложений.

Таблица организаций общая для enPlans и erespondentN, поэтому показываем
пользователей организации из всех приложений, сгруппированных по
приложению (текущее — первым): число, а по клику — список. У кого есть
почта, показываем почту, иначе логин.
"""

from markupsafe import Markup, escape

from .applications import get_current_application_id


def _label(user):
    text = user.email or user.login or f'Пользователь №{user.id}'
    suffix = ' · отключён' if user.is_active is False else ''
    return f'{escape(text)}{suffix}'


def org_accounts_cell(org):
    users = list(org.users)
    if not users:
        return '—'

    current = get_current_application_id()
    groups = {}
    for user in users:
        groups.setdefault(user.application_id, []).append(user)

    def group_name(app_id):
        sample = groups[app_id][0]
        return sample.application.name if sample.application else 'Без приложения'

    order = sorted(groups, key=lambda a: (a != current, a is None, group_name(a).lower()))
    items = []
    for app_id in order:
        members = sorted(groups[app_id], key=lambda u: (u.email or u.login or '').lower())
        items.append(f'<li class="ea-cell-group">{escape(group_name(app_id))} · {len(members)}</li>')
        items.extend(f'<li>{_label(u)}</li>' for u in members)
    return Markup(
        f'<details class="ea-cell-details"><summary>{len(users)}</summary>'
        f'<ul>{"".join(items)}</ul></details>'
    )


def org_egr_state_display(org):
    """Состояние организации по ЕГР словами (для карточки в админке)."""
    from .egr import STATUS_LABELS
    if not org.egr_status_kind:
        return 'Не сверялась с ЕГР'
    return STATUS_LABELS.get(org.egr_status_kind, org.egr_status_kind)


def org_egr_refresh(org):
    """Кнопка «Обновить из ЕГР» в карточке организации: наименования,
    юридический адрес, регион и статус по УНП. Возвращает список изменений;
    EgrError с понятным текстом — если обновить нельзя."""
    from .egr import refresh_organization
    return refresh_organization(org)
