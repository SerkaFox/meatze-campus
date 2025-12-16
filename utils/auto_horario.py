from datetime import date, timedelta, datetime, time
from django.core.cache import cache
import requests
from api.models import Curso


def is_holiday(fecha: date) -> bool:
    """Праздники ES/ES-PV + локальные неучебные + выходные."""
    year = fecha.year

    # 1) государственные праздники ES/ES-PV
    try:
        r = requests.get(f"https://date.nager.at/api/v3/PublicHolidays/{year}/ES", timeout=10)
        if r.status_code == 200:
            for h in r.json():
                counties = h.get("counties") or []
                # если counties есть, то берём только ES-PV
                if counties and "ES-PV" not in counties:
                    continue
                if h["date"] == fecha.isoformat():
                    return True
    except Exception as e:
        print("is_holiday: nager error:", e)

    # 2) локальные неучебные дни центра
    fixed = cache.get("mz_fixed_nonlective", {}) or {}
    # формат: {"2025": ["01-13", "01-15"], ...}
    arr = fixed.get(str(year), [])
    if arr:
        mmdd = fecha.strftime("%m-%d")
        if mmdd in arr:
            return True

    # 3) суббота/воскресенье
    if fecha.weekday() >= 5:
        return True

    return False


def auto_generate_schedule(curso_codigo, start_date, hours_per_day=5,
                           work_days=(0, 1, 2, 3, 4), grupo=None, tipo="curso"):
    """
    Генерация расписания курса.
    work_days = (0..6) → 0=Пн, 6=Вс
    """
    curso = Curso.objects.get(codigo=curso_codigo)
    mods = curso.modules or []

    items = []
    cursor = start_date

    for mod in mods:
        remaining = int(mod.get("hours", 0))
        name = mod.get("name", "")

        while remaining > 0:
            # 🔴 ключевая строка: праздник ИЛИ день не из work_days
            if cursor.weekday() not in work_days or is_holiday(cursor):
                cursor += timedelta(days=1)
                continue

            today_hours = min(hours_per_day, remaining)
            remaining -= today_hours

            desde = time(9, 0)
            hasta = (datetime.combine(date.today(), desde) +
                     timedelta(hours=today_hours)).time()

            items.append({
                "fecha": cursor.isoformat(),
                "desde": desde.strftime("%H:%M"),
                "hasta": hasta.strftime("%H:%M"),
                "aula": "",
                "nota": name,
                "tipo": tipo,
                "grupo": grupo,
            })

            cursor += timedelta(days=1)

    return items
