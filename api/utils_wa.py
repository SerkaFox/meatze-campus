# api/utils_wa.py
import re

def normalize_wa(raw) -> str:
    """
    Возвращает 9 цифр (ES):
    - убираем всё кроме цифр
    - убираем 0034 / 34
    - берём последние 9
    """
    s = re.sub(r"\D+", "", str(raw or ""))
    if not s:
        return ""

    if s.startswith("0034"):
        s = s[4:]
    elif s.startswith("34") and len(s) > 9:
        s = s[2:]

    if len(s) > 9:
        s = s[-9:]

    return s
