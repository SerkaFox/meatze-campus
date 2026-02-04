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
            nota  = (s.get("nota") or "").strip()
            # validate time format
            _parse_hhmm(desde)
            _parse_hhmm(hasta)
            norm.append({"id": sid, "desde": desde, "hasta": hasta, "aula": aula, "nota": nota})

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
                obj.modulo      = s["nota"]
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
        # ✅ ВАЖНО: балансировка после сохранения дня
        reb = _rebalance_schedule_to_target_minutes(curso, tipo, grupo)
    # return fresh day + aggregates
    # (перечитываем)
    qs = Horario.objects.filter(curso=curso).filter(layer).filter(dia=d)
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
        qs = Horario.objects.filter(curso=curso).filter(layer).filter(dia=d)
        deleted = qs.count()
        qs.delete()

    return JsonResponse({
        "ok": True,
        "deleted": deleted,
        "total_minutes_layer": _sum_layer_minutes(curso, tipo, grupo),
    })


@csrf_exempt
@require_admin_token
@require_http_methods(["GET", "POST"])
def horario_slot_delete(request, codigo: str, slot_id: int):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        return JsonResponse({"ok": False, "message": "Curso no encontrado"}, status=404)

    obj = Horario.objects.filter(id=slot_id, curso=curso).first()
    if not obj:
        return JsonResponse({"ok": False, "message": "Slot no encontrado"}, status=404)

    # Чтобы не снести чужой слой — можешь дополнительно проверять tipo/grupo из body
    obj.delete()
    return JsonResponse({"ok": True})

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
    # Фиксируем по horas_total курса (если есть)
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

def _rebalance_schedule_to_target_minutes(curso: Curso, tipo: str, grupo: str) -> Dict[str, Any]:
    with transaction.atomic():
        target = _get_target_minutes(curso)
        current = _sum_layer_minutes_db(curso, tipo, grupo)

        if target <= 0:
            return {"target_minutes": target, "before_minutes": current, "after_minutes": current, "delta_applied": 0, "mode": "no_target"}

        delta = current - target
        if delta == 0:
            return {"target_minutes": target, "before_minutes": current, "after_minutes": current, "delta_applied": 0, "mode": "ok"}

        qs = (
            _layer_queryset(curso, tipo, grupo)
            .select_for_update()
            .order_by("-dia", "-hora_inicio", "-hora_fin", "-id")
        )

    applied = 0

    if delta > 0:
        # нужно УБРАТЬ delta минут
        need_cut = delta

        for h in qs:
            m = _slot_minutes(h)
            if m <= 0:
                continue

            if need_cut >= m:
                # удалить целиком
                need_cut -= m
                applied += m
                h.delete()
            else:
                # укоротить слот на need_cut минут (с конца)
                fin_min = _tmin(h.hora_fin)
                new_fin = fin_min - need_cut
                if new_fin <= _tmin(h.hora_inicio):
                    # на всякий случай — если стало невалидно, удаляем
                    applied += m
                    h.delete()
                else:
                    h.hora_fin = _time_from_min(new_fin)
                    h.save(update_fields=["hora_fin"])
                    applied += need_cut
                need_cut = 0

            if need_cut <= 0:
                break

        after = _sum_layer_minutes_db(curso, tipo, grupo)
        return {
            "target_minutes": target,
            "before_minutes": current,
            "after_minutes": after,
            "delta_applied": applied,
            "mode": "cut_tail",
        }
    # delta < 0 => нужно ДОБАВИТЬ минут
    need_add = -delta

    pat = _dominant_day_pattern(curso, tipo, grupo)
    day_start = pat["day_start"]
    day_end   = pat["day_end"]          # ✅ вот твой потолок
    max_day_minutes = pat["day_minutes"] # ✅ сколько обычно часов в день


    # берём последнюю запись слоя (хвост), чтобы:
    #  - если есть место в дне: удлинить её
    #  - если нет: создавать новый день с тем же modulo/aula
    latest = (
        _layer_queryset(curso, tipo, grupo)
        .select_for_update()
        .order_by("-dia", "-hora_fin", "-id")
        .first()
    )

    if not latest:
        # если слоя вообще нет — тогда уже нечего "удлинять",
        # создаём первую запись нормальным шаблоном (но НЕ "(auto)")
        # тут можно выбрать любой дефолт для modulo
        base_mod = ""
        base_aula = ""
        d = _next_lective_day(date.today())
        hi = day_start
        chunk = min(need_add, max_day_minutes, max(0, _tmin(max_end) - _tmin(hi)))
        hf = _time_from_min(_tmin(hi) + chunk)

        obj = Horario(
            curso=curso,
            dia=d,
            tipo=("practica" if tipo == "practica" else "curso"),
            grupo=(grupo if tipo == "practica" else ""),
            hora_inicio=hi,
            hora_fin=hf,
            aula=base_aula,
            modulo=base_mod,
        )
        obj.save()
        applied += chunk
        need_add -= chunk
        latest = obj

    # запоминаем “последний модуль”, чтобы переносить его на новые дни
    base_mod = (latest.modulo or "")
    base_aula = (latest.aula or "")

    while need_add > 0 and latest:
        d = latest.dia

        # конец текущего дня: max(hora_fin) в этом дне
        last_in_day = (
            _layer_queryset(curso, tipo, grupo)
            .select_for_update()
            .filter(dia=d)
            .order_by("-hora_fin", "-id")
            .first()
        )

        # ✅ ключевая идея: расширяем ПОСЛЕДНИЙ слот дня (не создаём новый)
        tail = last_in_day or latest

        start_min = _tmin(tail.hora_fin) if tail.hora_fin else _tmin(day_start)
        end_cap = _tmin(day_end)
        free = max(0, end_cap - start_min)

        if free > 0:
            chunk = min(need_add, free, max_day_minutes)

            new_fin_min = start_min + chunk
            tail.hora_fin = _time_from_min(new_fin_min)
            tail.save(update_fields=["hora_fin"])

            applied += chunk
            need_add -= chunk

            # latest должен указывать на реальный хвост
            latest = tail
            continue

        # если в текущем дне места нет — создаём НОВЫЙ день
        next_day = _next_lective_day(d + timedelta(days=1))


        # новый слот: 09:00-... с ТЕМ ЖЕ modulo/aula (не "(auto)")
        hi = day_start
        free2 = max(0, _tmin(day_end) - _tmin(hi))
        if free2 <= 0:
            # теоретически не случится, но пусть будет
            break

        chunk = min(need_add, free2, max_day_minutes)
        hf = _time_from_min(_tmin(hi) + chunk)

        obj = Horario(
            curso=curso,
            dia=next_day,
            tipo=("practica" if tipo == "practica" else "curso"),
            grupo=(grupo if tipo == "practica" else ""),
            hora_inicio=hi,
            hora_fin=hf,
            aula=base_aula,
            modulo=base_mod,
        )
        obj.save()
        applied += chunk
        need_add -= chunk
        latest = obj

    after = _sum_layer_minutes_db(curso, tipo, grupo)
    return {
        "target_minutes": target,
        "before_minutes": current,
        "after_minutes": after,
        "delta_applied": applied,
        "mode": "add_tail_extend_last",
    }



from collections import Counter, defaultdict
from datetime import timedelta

def _tmin(t: time) -> int:
    return t.hour * 60 + t.minute

def _time_from_min(m: int) -> time:
    m = max(0, min(23*60 + 59, m))
    return time(m // 60, m % 60)

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
