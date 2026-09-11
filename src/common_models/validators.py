"""Валидация реквизитов организации — общая для enPlans и ErespondentN.

Правила перенесены из ErespondentN (website/organization.py), где они уже
использовались при ручном редактировании данных организации (форма на
главной странице); здесь они переиспользуются ботом автоматической
переписки enPlans в виджете виртуального помощника (обращение «Изменить
данные организации»).
"""


def validate_okpo(okpo):
    """ОКПО — 12 цифр, 4-я с конца цифра (код орг.-правовой формы) — от 1 до 7."""
    if not okpo or not okpo.isdigit() or len(okpo) != 12:
        return False, "ОКПО должен содержать 12 цифр"
    fourth_from_end = okpo[-4]
    allowed_digits = ['1', '2', '3', '4', '5', '6', '7']
    if fourth_from_end not in allowed_digits:
        return False, "4-я цифра с конца в коде ОКПО должна быть от 1 до 7"
    return True, ""


def validate_ynp(ynp):
    """УНП — ровно 9 цифр."""
    if not ynp or not ynp.isdigit() or len(ynp) != 9:
        return False, "УНП должен содержать ровно 9 цифр"
    return True, ""
