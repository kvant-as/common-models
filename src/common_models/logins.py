"""Логины учётных записей сотрудников (enPlans).

Логин строится как «первая буква имени + точка + фамилия» латиницей
(i.ivanov). Транслитерация — по ICAO Doc 9303, которая используется в
паспортах Республики Беларусь для латинского написания имён: без
диакритики, только a–z, поэтому подходит для логина.
"""
import re
import secrets
import string

TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': 'ie', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'iu', 'я': 'ia',
    'і': 'i', 'ў': 'u', "'": '', '’': '',
}

LOGIN_RE = re.compile(r'^[a-z0-9][a-z0-9._-]{1,62}[a-z0-9]$')
LOGIN_MAX = 64
PASSWORD_MIN = 8
PASSWORD_ALPHABET = ''.join(c for c in string.ascii_letters + string.digits if c not in 'O0Il1')


def transliterate(text):
    out = []
    for ch in (text or '').strip().lower():
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif 'a' <= ch <= 'z' or ch.isdigit():
            out.append(ch)
        elif ch in ' -':
            out.append('-')
    return re.sub(r'-+', '-', ''.join(out)).strip('-')


def normalize_login(value):
    return (value or '').strip().lower()


def validate_login(value):
    """Ошибка (строка) или None."""
    login = normalize_login(value)
    if not login:
        return 'Укажите логин'
    if len(login) > LOGIN_MAX:
        return f'Логин не длиннее {LOGIN_MAX} символов'
    if not LOGIN_RE.match(login):
        return 'Логин: латинские буквы, цифры, точка, дефис или подчёркивание, от 3 символов'
    return None


def login_candidates(first_name, last_name):
    """i.ivanov → iv.ivanov → i.ivanov2, i.ivanov3, …"""
    first = transliterate(first_name)
    last = transliterate(last_name) or 'user'
    base = f'{first[:1]}.{last}' if first else last
    yield base
    if len(first) > 1:
        yield f'{first[:2]}.{last}'
    n = 2
    while True:
        yield f'{base}{n}'
        n += 1


def generate_login(first_name, last_name, is_taken):
    """Первый свободный вариант; is_taken(login) -> bool."""
    for candidate in login_candidates(first_name, last_name):
        candidate = candidate[:LOGIN_MAX]
        if not is_taken(candidate):
            return candidate


def generate_password(length=10):
    while True:
        pwd = ''.join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))
        if any(c.isdigit() for c in pwd) and any(c.isalpha() for c in pwd):
            return pwd
