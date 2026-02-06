# api/views_horario_day.py
from __future__ import annotations

from datetime import date, datetime, time
from typing import Dict, Any, List, Tuple
from api.models import MZSetting

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from api.models import Curso, Horario  # поправь импорт под свои пути
from .decorators import require_admin_token  # <-- твой декоратор/проверка токена

from django.views.decorators.csrf import csrf_exempt


# ---------- helpers ----------

def _parse_iso_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("date inválida (YYYY-MM-DD)")

def _parse_hhmm(s: str) -> time:
    s = (s or "").strip()
    try:
        # допускаем "09:00" или "09:00:00"
        if len(s) == 5:
            return time.fromisoformat(s)
        return time.fromisoformat(s[:8])
    except Exception:
        raise ValueError("hora inválida (HH:MM)")

def _minutes(t1: time, t2: time) -> int:
    a = t1.hour * 60 + t1.minute
    b = t2.hour * 60 + t2.minute
    return b - a

def _layer_q(tipo: str, grupo: str) -> Q:
    tipo = (tipo or "curso").strip().lower()
    grupo = (grupo or "").strip()

    if tipo == "practica":
        # практика: строго tipo="practica" + группа обязательна
        if not grupo:
            raise ValueError("grupo es obligatorio para práctica")
        return Q(tipo="practica", grupo=grupo)

    # курс: считаем курсом NULL/""/"curso"
    return (Q(tipo__isnull=True) | Q(tipo="") | Q(tipo="curso"))

def _serialize_slot(obj: Horario) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "date": obj.dia.isoformat(),
        "desde": (obj.hora_inicio.strftime("%H:%M") if obj.hora_inicio else ""),
        "hasta": (obj.hora_fin.strftime("%H:%M") if obj.hora_fin else ""),
        "aula": obj.aula or "",
        "nota": obj.modulo or "",
        "tipo": (obj.tipo or "").strip(),
        "grupo": (obj.grupo or "").strip(),
    }

def _sum_layer_minutes(curso: Curso, tipo: str, grupo: str) -> int:
    qs = Horario.objects.filter(curso=curso).filter(_layer_q(tipo, grupo))
    total = 0
    for it in qs.only("hora_inicio", "hora_fin"):
        if it.hora_inicio and it.hora_fin:
            total += _minutes(it.hora_inicio, it.hora_fin)
    return max(0, total)


def _sum_day_minutes(items: List[Dict[str, Any]]) -> int:
    total = 0
    for x in items:
        try:
            total += _minutes(_parse_hhmm(x["desde"]), _parse_hhmm(x["hasta"]))
        except Exception:
            pass
    return max(0, total)

def _validate_no_overlap(slots: List[Dict[str, Any]]) -> None:
    # запретим пересечения внутри дня
    spans: List[Tuple[int,int]] = []
    for s in slots:
        t1 = _parse_hhmm(s["desde"])
        t2 = _parse_hhmm(s["hasta"])
        m = _minutes(t1, t2)
        if m <= 0:
            raise ValueError("desde debe ser menor que hasta")
        a = t1.hour*60 + t1.minute
        b = t2.hour*60 + t2.minute
        spans.append((a,b))

    spans.sort()
    for i in range(1, len(spans)):
        if spans[i][0] < spans[i-1][1]:
            raise ValueError("hay solapamiento entre tramos")


# ---------- endpoints ----------

@csrf_exempt
@require_admin_token
@require_http_methods(["GET", "POST"])
def horario_day(request, codigo: str):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        return JsonResponse({"ok": False, "message": "Curso no encontrado"}, status=404)

    if request.method == "GET":
        date_str = (request.GET.get("date") or "").strip()
        tipo = (request.GET.get("tipo") or "curso").strip().lower()
        grupo = (request.GET.get("grupo") or "").strip()

        try:
            d = _parse_iso_date(date_str)
            layer = _layer_q(tipo, grupo)
        except ValueError as e:
            return JsonResponse({"ok": False, "message": str(e)}, status=400)

        qs = Horario.objects.filter(curso=curso).filter(layer)

        # поле даты у тебя может называться dia/fecha — подстрой:
        if hasattr(Horario, "dia"):
            qs = qs.filter(dia=d)
        else:
            qs = qs.filter(fecha=d.isoformat())

        items = [_serialize_slot(x) for x in qs.order_by("hora_inicio", "hora_fin")]

        return JsonResponse({
            "ok": True,
            "date": d.isoformat(),
            "tipo": tipo,
            "grupo": grupo,
            "items_day": items,
            "day_minutes": _sum_day_minutes(items),
            "total_minutes_layer": _sum_layer_minutes(curso, tipo, grupo),
        })

    # POST: upsert slots for day
    import json
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    tipo = (body.get("tipo") or "curso").strip().lower()
    grupo = (body.get("grupo") or "").strip()
    date_str = (body.get("date") or "").strip()
    slots = body.get("slots") or []

    if not isinstance(slots, list):
        return JsonResponse({"ok": False, "message": "slots debe ser lista"}, status=400)

    try:
        d = _parse_iso_date(date_str)
        layer = _layer_q(tipo, grupo)
        # нормализуем slots
        norm: List[Dict[str, Any]] = []
        for s in slots:
            if not isinstance(s, dict):
                continue
            sid = s.get("id")
            desde = (s.get("desde") or "").strip()
            hasta = (s.get("hasta") or "").strip()
            aula  = (s.get("aula") or "").strip()
            module_key = (s.get("module_key") or "").strip()  # надо начать слать это из фронта
            nota = (s.get("nota") or "").strip()
            # validate time format
            _parse_hhmm(desde)
            _parse_hhmm(hasta)
            norm.append({"id": sid, "desde": desde, "hasta": hasta, "aula": aula, "nota": nota,  "module_key": module_key})

        _validate_no_overlap(norm)

    except ValueError as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=400)

    with transaction.atomic():
        qs = Horario.objects.select_for_update().filter(curso=curso).filter(layer)
        if hasattr(Horario, "dia"):
            qs = qs.filter(dia=d)
        else:
            qs = qs.filter(fecha=d.isoformat())

        existing = {x.id: x for x in qs}

        keep_ids = set()
        # update/create
        for s in norm:
            sid = s.get("id")
            if sid and sid in existing:
                obj = existing[sid]
                obj.hora_inicio = _parse_hhmm(s["desde"])
                obj.hora_fin    = _parse_hhmm(s["hasta"])
                obj.aula        = s["aula"]
                obj.modulo      = module_key
                obj.save(update_fields=["hora_inicio", "hora_fin", "aula", "modulo"])

                keep_ids.add(obj.id)
            else:
                obj = Horario(
                    curso=curso,
                    dia=d,
                    tipo=("practica" if tipo == "practica" else "curso"),
                    grupo=(grupo if tipo == "practica" else ""),
                    hora_inicio=_parse_hhmm(s["desde"]),
                    hora_fin=_parse_hhmm(s["hasta"]),
                    aula=s["aula"],
                    modulo=s["nota"],
                )
                obj.save()
                keep_ids.add(obj.id)

        # delete removed
        for eid, obj in existing.items():
            if eid not in keep_ids:
                obj.delete()
        # ✅ 1) сначала перепривязать модули внутри anchor day
        assign = _reassign_modules_for_day(curso, tipo, grupo, d)

        # ✅ 2) потом пересобрать хвост
        reb = _reflow_modules_chain(curso, tipo, grupo, anchor_date=d, keep_anchor_day=True)

        # и верни assign тоже для дебага
    # return fresh day + aggregates
    # (перечитываем)
    qs = Horario.objects.filter(curso=curso).filter(layer)
    if hasattr(Horario, "dia"):
        qs = qs.filter(dia=d)
    else:
        qs = qs.filter(fecha=d.isoformat())
    items = [_serialize_slot(x) for x in qs.order_by("hora_inicio", "hora_fin")]


    return JsonResponse({
        "ok": True,
        "date": d.isoformat(),
        "tipo": tipo,
        "grupo": grupo,
        "items_day": items,
        "day_minutes": _sum_day_minutes(items),
        "total_minutes_layer": _sum_layer_minutes(curso, tipo, grupo),
        "rebalance": reb,   # ✅
    })



@csrf_exempt
@require_admin_token
@require_http_methods(["GET", "POST"])
def horario_day_delete(request, codigo: str):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        return JsonResponse({"ok": False, "message": "Curso no encontrado"}, status=404)

    import json
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    tipo = (body.get("tipo") or "curso").strip().lower()
    grupo = (body.get("grupo") or "").strip()
    date_str = (body.get("date") or "").strip()

    try:
        d = _parse_iso_date(date_str)
        layer = _layer_q(tipo, grupo)
    except ValueError as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=400)

    with transaction.atomic():
        qs = Horario.objects.select_for_update().filter(curso=curso).filter(layer).filter(dia=d)
        deleted = qs.count()
        qs.delete()

        assign = _reassign_modules_for_day(curso, tipo, grupo, d)
        reb = _reflow_modules_chain(curso, tipo, grupo, anchor_date=d, keep_anchor_day=True)

    return JsonResponse({
        "ok": True,
        "deleted": deleted,
        "total_minutes_layer": _sum_layer_minutes(curso, tipo, grupo),
        "rebalance": reb,
    })

@csrf_exempt
@require_admin_token
@require_http_methods(["POST"])
def horario_slot_delete(request, codigo: str, slot_id: int):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        return JsonResponse({"ok": False, "message": "Curso no encontrado"}, status=404)

    obj = Horario.objects.filter(id=slot_id, curso=curso).first()
    if not obj:
        return JsonResponse({"ok": False, "message": "Slot no encontrado"}, status=404)

    # слой берём из удаляемого слота (самый надёжный вариант)
    tipo = (obj.tipo or "curso").strip().lower()
    grupo = (obj.grupo or "").strip()
    d = obj.dia

    # важно: если tipo="practica", но grupo пустой — _layer_q() у тебя кинет ValueError
    # значит нужно либо запрещать такие слоты, либо тут подстраховаться:
    if tipo == "practica" and not grupo:
        return JsonResponse({"ok": False, "message": "grupo es obligatorio para práctica"}, status=400)

    layer = _layer_q(tipo, grupo)

    with transaction.atomic():
        # удаляем слот
        Horario.objects.select_for_update().filter(id=obj.id).delete()

        # 1) перепривязать модули дня
        assign = _reassign_modules_for_day(curso, tipo, grupo, d)

        # 2) пересобрать хвост
        reb = _reflow_modules_chain(curso, tipo, grupo, anchor_date=d, keep_anchor_day=True)

    return JsonResponse({
        "ok": True,
        "date": d.isoformat(),
        "tipo": tipo,
        "grupo": grupo,
        "total_minutes_layer": _sum_layer_minutes(curso, tipo, grupo),
        "assign": assign,
        "rebalance": reb,
    })

from datetime import timedelta

def _tmin(t: time) -> int:
    return t.hour * 60 + t.minute

def _time_from_min(m: int) -> time:
    m = max(0, min(23*60+59, m))
    return time(m // 60, m % 60)

def _slot_minutes(h: Horario) -> int:
    if not h.hora_inicio or not h.hora_fin:
        return 0
    return max(0, _minutes(h.hora_inicio, h.hora_fin))

def _layer_queryset(curso: Curso, tipo: str, grupo: str):
    return Horario.objects.filter(curso=curso).filter(_layer_q(tipo, grupo))

def _sum_layer_minutes_db(curso: Curso, tipo: str, grupo: str) -> int:
    total = 0
    for it in _layer_queryset(curso, tipo, grupo).only("hora_inicio", "hora_fin"):
        if it.hora_inicio and it.hora_fin:
            total += _minutes(it.hora_inicio, it.hora_fin)
    return max(0, total)

def _get_target_minutes(curso: Curso) -> int:
    # 1) пробуем из JSON modules
    mods = getattr(curso, "modules", None)
    if isinstance(mods, list) and mods:
        total_h = 0
        for m in mods:
            try:
                total_h += int(m.get("hours") or m.get("horas") or 0)
            except Exception:
                pass
        if total_h > 0:
            return total_h * 60

    # 2) иначе horas_total как fallback
    try:
        horas = int(getattr(curso, "horas_total", 0) or 0)
    except Exception:
        horas = 0
    return max(0, horas * 60)


def _extend_slot(obj: Horario, add_minutes: int) -> int:
    """
    Пытается удлинить obj.hora_fin на add_minutes.
    Возвращает сколько реально добавили.
    """
    if not obj.hora_inicio or not obj.hora_fin:
        return 0

    cur = obj.hora_fin.hour * 60 + obj.hora_fin.minute
    new = cur + max(0, int(add_minutes))

    # если у тебя есть ограничение по "концу дня" — включи:
    # DAY_END = 20 * 60
    # new = min(new, DAY_END)

    hh = new // 60
    mm = new % 60
    obj.hora_fin = time(hh % 24, mm)   # (обычно хватит, но лучше не уходить за 24:00)
    obj.save(update_fields=["hora_fin"])
    return max(0, int(add_minutes))   # если не ограничиваем — всё добавили


from django.db import transaction
from datetime import timedelta
from typing import Dict, Any, List, Tuple, Optional
import json
def _get_layer_plan(curso: Curso, tipo: str, grupo: str) -> List[Tuple[str, int]]:
    """
    Возвращает план (module_key, minutes_target) для конкретного слоя.
    - curso: берём из curso.modules (как было)
    - practica: делаем 1 “модуль” PRACTICA на весь target (или по группам)
    """
    tipo = (tipo or "curso").strip().lower()
    grupo = (grupo or "").strip()

    if tipo == "practica":
        target = _get_practica_target_minutes(curso, grupo)  # см. ниже
        if target > 0:
            key = f"PRACTICA {grupo}".strip() if grupo else "PRACTICA"
            return [(key, target)]
        return []

    # ---- curso (как раньше) ----
    raw = getattr(curso, "modules", None)

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = []

    if not isinstance(raw, list):
        raw = []

    plan: List[Tuple[str, int]] = []
    for i, m in enumerate(raw):
        if not isinstance(m, dict):
            continue
        key = str(m.get("code") or m.get("cod") or m.get("name") or m.get("key") or f"M{i+1}").strip()
        try:
            horas = float(m.get("hours") or m.get("horas") or 0)
        except Exception:
            horas = 0
        mins = int(max(0, round(horas * 60)))
        if key and mins > 0:
            plan.append((key, mins))

    return plan

def _get_practica_target_minutes(curso: Curso, grupo: str) -> int:
    """
    Варианты:
    1) фикс настройкой: MZSetting key="practica_hours" -> {"default": 80, "by_course": {"IFCT0309": 120}}
    2) или просто key="practica_hours_default" -> 80
    """
    grupo = (grupo or "").strip()

    cfg = MZSetting.objects.filter(key="practica_hours").only("value").first()
    val = (cfg.value if cfg else {}) or {}

    # by_course: по коду курса
    by_course = (val.get("by_course") or {}) if isinstance(val, dict) else {}
    if isinstance(by_course, dict):
        h = by_course.get(getattr(curso, "codigo", ""), None)
        if h is not None:
            try:
                return int(float(h) * 60)
            except Exception:
                pass

    # default
    default_h = val.get("default", None) if isinstance(val, dict) else None
    if default_h is not None:
        try:
            return int(float(default_h) * 60)
        except Exception:
            return 0

    # fallback вообще
    return 0

def _sum_minutes_qs(qs) -> int:
    total = 0
    for it in qs.only("hora_inicio", "hora_fin"):
        if it.hora_inicio and it.hora_fin:
            total += max(0, _minutes(it.hora_inicio, it.hora_fin))
    return max(0, total)


def _advance_in_plan(plan: List[Tuple[str, int]], consumed: int) -> Tuple[int, int]:
    """
    По количеству уже отученных минут возвращает:
      - индекс текущего модуля в plan
      - сколько минут осталось ДОУЧИТЬ в этом модуле
    """
    idx = 0
    while idx < len(plan) and consumed > 0:
        _, need = plan[idx]
        if consumed >= need:
            consumed -= need
            idx += 1
        else:
            need -= consumed
            consumed = 0
            return idx, need

    if idx >= len(plan):
        return len(plan), 0

    return idx, plan[idx][1]


def _reflow_modules_chain(
    curso: Curso,
    tipo: str,
    grupo: str,
    anchor_date: date,
    keep_anchor_day: bool = True,
) -> Dict[str, Any]:
    tipo = (tipo or "curso").strip().lower()
    grupo = (grupo or "").strip()

    plan = _get_layer_plan(curso, tipo, grupo)
    if not plan:
        return {"ok": True, "mode": "no_plan"}

    target_total = sum(m for _, m in plan)
    if target_total <= 0:
        return {"ok": True, "mode": "no_target"}

    layer = _layer_q(tipo, grupo)

    pat = _dominant_day_pattern(curso, tipo, grupo)
    day_start: time = pat["day_start"]
    day_end: time   = pat["day_end"]

    day_start_min = _tmin(day_start)
    day_end_min   = _tmin(day_end)
    if day_end_min <= day_start_min:
        day_start_min = 9 * 60
        day_end_min   = 14 * 60

    cutoff = anchor_date if keep_anchor_day else (anchor_date - timedelta(days=1))

    qs_before = (
        Horario.objects
        .filter(curso=curso).filter(layer)
        .filter(dia__lte=cutoff)
        .order_by("dia", "hora_inicio", "hora_fin", "id")
    )
    consumed_before = _sum_minutes_qs(qs_before)

    idx, left_in_mod = _advance_in_plan(plan, min(consumed_before, target_total))

    reflow_from = anchor_date + timedelta(days=1) if keep_anchor_day else anchor_date
    qs_tail = Horario.objects.select_for_update().filter(curso=curso).filter(layer).filter(dia__gte=reflow_from)
    deleted = qs_tail.count()
    qs_tail.delete()

    if idx >= len(plan):
        after = _sum_layer_minutes_db(curso, tipo, grupo)
        return {
            "ok": True,
            "mode": "done_before_anchor",
            "target_minutes": target_total,
            "before_minutes": consumed_before,
            "after_minutes": after,
            "deleted_tail": deleted,
        }

    last_before = (
        Horario.objects
        .filter(curso=curso).filter(layer)
        .filter(dia__lte=cutoff)
        .order_by("-dia", "-hora_fin", "-id")
        .first()
    )
    base_aula = (last_before.aula or "") if last_before else ""

    remaining_total = target_total - min(consumed_before, target_total)

    dcur = _next_lective_day(reflow_from)

    created = 0
    safety_days = 0

    while remaining_total > 0 and idx < len(plan):
        safety_days += 1
        if safety_days > 900:
            break

        dcur = _next_lective_day(dcur)

        free_day = max(0, day_end_min - day_start_min)
        if free_day <= 0:
            break

        cursor_min = day_start_min

        while remaining_total > 0 and free_day > 0 and idx < len(plan):
            mod_key, _ = plan[idx]
            take = min(free_day, left_in_mod, remaining_total)
            if take <= 0:
                break

            hi = _time_from_min(cursor_min)
            hf = _time_from_min(cursor_min + take)

            Horario.objects.create(
                curso=curso,
                dia=dcur,
                tipo=("practica" if tipo == "practica" else "curso"),
                grupo=(grupo if tipo == "practica" else ""),
                hora_inicio=hi,
                hora_fin=hf,
                aula=base_aula,
                modulo=mod_key,
            )
            created += 1

            cursor_min += take
            free_day   -= take
            remaining_total -= take
            left_in_mod -= take

            if left_in_mod <= 0:
                idx += 1
                if idx < len(plan):
                    left_in_mod = plan[idx][1]

        dcur = dcur + timedelta(days=1)

    after = _sum_layer_minutes_db(curso, tipo, grupo)
    return {
        "ok": True,
        "mode": "reflow_after_anchor",
        "target_minutes": target_total,
        "before_minutes": consumed_before,
        "after_minutes": after,
        "deleted_tail": deleted,
        "created_slots": created,
        "anchor_date": anchor_date.isoformat(),
        "reflow_from": reflow_from.isoformat(),
        "tipo": tipo,
        "grupo": grupo,
    }

from collections import Counter, defaultdict
from datetime import timedelta


def _dominant_day_pattern(curso: Curso, tipo: str, grupo: str) -> dict:
    """
    Возвращает самый частый (start,end,total) паттерн дня для данного слоя.
    """
    qs = _layer_queryset(curso, tipo, grupo).only("dia", "hora_inicio", "hora_fin")

    by_day = defaultdict(list)
    for h in qs:
        if h.dia and h.hora_inicio and h.hora_fin:
            by_day[h.dia].append(h)

    if not by_day:
        return {
            "day_start": time(9,0),
            "day_end": time(14,0),
            "day_minutes": 5*60,
        }

    patterns = []
    for d, slots in by_day.items():
        starts = [_tmin(s.hora_inicio) for s in slots]
        ends   = [_tmin(s.hora_fin) for s in slots]
        start_min = min(starts)
        end_min   = max(ends)

        total = 0
        for s in slots:
            total += max(0, _tmin(s.hora_fin) - _tmin(s.hora_inicio))

        patterns.append((start_min, end_min, total))

    # мода по (start,end); если равны — по total
    c = Counter((a,b) for a,b,_ in patterns)
    (dom_start, dom_end), _freq = c.most_common(1)[0]

    # для day_minutes берём наиболее частый total среди дней с тем же (start,end)
    totals = [tot for a,b,tot in patterns if a == dom_start and b == dom_end]
    if totals:
        day_minutes = Counter(totals).most_common(1)[0][0]
    else:
        day_minutes = max(0, dom_end - dom_start)

    return {
        "day_start": _time_from_min(dom_start),
        "day_end": _time_from_min(dom_end),
        "day_minutes": int(day_minutes),
    }


def _fixed_nonlective_set_for_year(y: int) -> set[str]:
    cfg = MZSetting.objects.filter(key="fixed_nonlective").only("value").first()
    years = (cfg.value if cfg else {}) or {}
    arr = years.get(str(y), []) or []
    return set(str(x).strip() for x in arr if str(x).strip())

def _is_nonlective(d: date) -> bool:
    if d.weekday() >= 5:
        return True
    fixed = _fixed_nonlective_set_for_year(d.year)
    if d.strftime("%m-%d") in fixed:
        return True
    return False

def _next_lective_day(d: date) -> date:
    cur = d
    while _is_nonlective(cur):
        cur += timedelta(days=1)
    return cur

def _reassign_modules_for_day(curso: Curso, tipo: str, grupo: str, d: date) -> Dict[str, Any]:
    plan = _get_layer_plan(curso, tipo, grupo)
    if not plan:
        return {"ok": True, "mode": "no_plan"}

    layer = _layer_q(tipo, grupo)

    qs_before = (
        Horario.objects.filter(curso=curso).filter(layer)
        .filter(dia__lt=d)
        .order_by("dia", "hora_inicio", "hora_fin", "id")
    )
    consumed = _sum_minutes_qs(qs_before)

    target_total = sum(m for _, m in plan)
    idx, left_in_mod = _advance_in_plan(plan, min(consumed, target_total))

    qs_day = (
        Horario.objects.select_for_update()
        .filter(curso=curso).filter(layer)
        .filter(dia=d)
        .order_by("hora_inicio", "hora_fin", "id")
    )

    changed = 0
    for h in qs_day:
        mins = _slot_minutes(h)
        if mins <= 0:
            continue
        if idx >= len(plan):
            break

        h.modulo = plan[idx][0]
        h.save(update_fields=["modulo"])
        changed += 1

        left_in_mod -= mins
        while left_in_mod <= 0 and idx < len(plan) - 1:
            idx += 1
            left_in_mod += plan[idx][1]

    return {"ok": True, "changed": changed}