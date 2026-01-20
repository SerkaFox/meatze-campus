# api/views_events.py
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Sum, Max, Min
from django.db.models.functions import TruncDate
from api.utils_events import log_event
from api.models import LearningEvent
from api.decorators import require_admin_token  
from django.contrib.auth import get_user_model
from api.models import Enrol, UserProfile
User = get_user_model()

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # отключаем CSRF

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def log_learning_event(request):
    data = request.data or {}

    ev = (data.get("event") or "").strip()[:50]
    if not ev:
        return Response({"error": "event_required"}, status=status.HTTP_400_BAD_REQUEST)

    curso_codigo = (data.get("curso_codigo") or "").strip()[:32]
    session_id = (data.get("session_id") or "").strip()[:64]

    seq = data.get("seq")
    try:
        seq = int(seq) if seq is not None else None
    except Exception:
        seq = None

    obj_type = (data.get("object_type") or "").strip()[:50]
    obj_id = (data.get("object_id") or "").strip()[:64]
    page = (data.get("page") or "").strip()[:200]
    ref = (data.get("ref") or "").strip()[:200]
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    ts = data.get("ts")

    e = log_event(
        request,
        event=ev,
        curso_codigo=curso_codigo,
        object_type=obj_type,
        object_id=obj_id,
        meta=meta,
        session_id=session_id,
        seq=seq,
        page=page,
        ref=ref,
        client_ts=ts,
    )

    return Response({"ok": True, "id": (e.id if e else None)})


def _parse_ymd(s: str):
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None


def _display_name(user, profile: UserProfile | None):
    if not user:
        return ""
    # приоритет: display_name -> first/last1/last2 -> user.get_full_name -> email/username
    disp = (getattr(profile, "display_name", "") or "").strip() if profile else ""
    if disp:
        return disp

    first = ((getattr(profile, "first_name", "") if profile else "") or user.first_name or "").strip()
    last1 = ((getattr(profile, "last_name1", "") if profile else "") or user.last_name or "").strip()
    last2 = ((getattr(profile, "last_name2", "") if profile else "") or "").strip()

    full = " ".join([x for x in [first, last1, last2] if x]).strip()
    if full:
        return full

    return (user.get_full_name() or getattr(user, "email", "") or user.username or "").strip()


@require_admin_token
@require_http_methods(["GET"])
def admin_lanbide_activity(request):
    codigo = (request.GET.get("codigo") or "").strip()
    if not codigo:
        return JsonResponse({"ok": False, "error": "codigo_required"}, status=400)

    dfrom = _parse_ymd((request.GET.get("from") or "").strip())
    dto = _parse_ymd((request.GET.get("to") or "").strip())

    qs = LearningEvent.objects.filter(curso_codigo=codigo)

    if dfrom:
        qs = qs.filter(created_at__date__gte=dfrom)
    if dto:
        qs = qs.filter(created_at__date__lte=dto)

    rows = list(
        qs.values("user_id")
        .annotate(
            events=Count("id"),
            last=Max("created_at"),
            raw_delta=Sum("delta_sec"),
        )
        .order_by("user_id")
    )
    

    cap = 120  # максимум "активности" между кликами (сек)
    active_map = {}
    for uid in [r["user_id"] for r in rows]:
        deltas = list(qs.filter(user_id=uid).values_list("delta_sec", flat=True))
        active_map[uid] = int(sum(min(int(x or 0), cap) for x in deltas))

    total_events = sum(int(r["events"] or 0) for r in rows)
    total_active = sum(active_map.values())

    # --- подтягиваем имена одним запросом (без N+1) ---
    user_ids = [r["user_id"] for r in rows if r.get("user_id")]

    users_by_id = {u.id: u for u in User.objects.filter(id__in=user_ids)}
    prof_by_uid = {p.user_id: p for p in UserProfile.objects.filter(user_id__in=user_ids)}

    # роль по курсу
    enrols = Enrol.objects.filter(codigo=codigo, user_id__in=user_ids).values("user_id", "role")
    role_by_uid = {e["user_id"]: e["role"] for e in enrols}   # "teacher"/"student"

    role_q = (request.GET.get("role") or "").strip().lower()  # student|teacher|''

    def _display_name(user, profile):
        if not user:
            return ""
        disp = (getattr(profile, "display_name", "") or "").strip() if profile else ""
        if disp:
            return disp
        first = ((getattr(profile, "first_name", "") if profile else "") or user.first_name or "").strip()
        last1 = ((getattr(profile, "last_name1", "") if profile else "") or user.last_name or "").strip()
        last2 = ((getattr(profile, "last_name2", "") if profile else "") or "").strip()
        full = " ".join([x for x in [first, last1, last2] if x]).strip()
        return full or (user.get_full_name() or user.email or user.username or "").strip()

    out = []
    for r in rows:
        uid = r["user_id"]
        u = users_by_id.get(uid)
        p = prof_by_uid.get(uid)

        role = role_by_uid.get(uid, "unknown")
        if role_q in ("student", "teacher") and role != role_q:
            continue

        out.append({
            "user_id": uid,
            "name": _display_name(u, p),
            "role": role,
            "events": int(r["events"] or 0),
            "active_sec": int(active_map.get(uid, 0)),
            "last": (r["last"].isoformat() if r["last"] else None),
        })


    return JsonResponse({
        "ok": True,
        "codigo": codigo,
        "range": {"from": (dfrom.isoformat() if dfrom else None), "to": (dto.isoformat() if dto else None)},
        "total_events": total_events,
        "total_active_sec": total_active,
        "users": out,
    })


@require_admin_token
@require_http_methods(["GET"])
def admin_lanbide_daily(request):
    """
    GET /meatze/v5/admin/lanbide/daily?codigo=IFCT0309&from=2026-01-12&to=2026-01-14&role=student
    Возвращает строки (user, day): events, active_sec, first, last
    """

    codigo = (request.GET.get("codigo") or "").strip()
    if not codigo:
        return JsonResponse({"ok": False, "error": "codigo_required"}, status=400)

    dfrom = _parse_ymd((request.GET.get("from") or "").strip())
    dto = _parse_ymd((request.GET.get("to") or "").strip())

    role_q = (request.GET.get("role") or "").strip().lower()  # student|teacher|''

    qs = LearningEvent.objects.filter(curso_codigo=codigo)

    if dfrom:
        qs = qs.filter(created_at__date__gte=dfrom)
    if dto:
        qs = qs.filter(created_at__date__lte=dto)

    # --- фильтр по роли через Enrol (самый правильный для курса) ---
    # если role задан — ограничиваем user_id
    if role_q in ("student", "teacher"):
        allowed_ids = list(
            Enrol.objects.filter(codigo=codigo, role=role_q).values_list("user_id", flat=True)
        )
        if not allowed_ids:
            return JsonResponse({
                "ok": True,
                "codigo": codigo,
                "range": {"from": (dfrom.isoformat() if dfrom else None), "to": (dto.isoformat() if dto else None)},
                "rows": [],
            })
        qs = qs.filter(user_id__in=allowed_ids)

    # --- агрегация по дням ---
    rows = list(
        qs.annotate(day=TruncDate("created_at"))
          .values("user_id", "day")
          .annotate(
              events=Count("id"),
              active_sec=Sum("delta_sec"),
              first=Min("created_at"),
              last=Max("created_at"),
          )
          .order_by("user_id", "day")
    )

    # --- cap delta_sec (если в БД уже cap'ишь, это будет совпадать; если нет — сделаем безопаснее) ---
    cap = 120
    # если хочешь железно-cap даже если где-то записали больше:
    # пересчитаем active_sec через суммирование по raw deltas
    # (это чуть тяжелее, но диапазоны обычно небольшие)
    active_map = {}
    for r in rows:
        key = (r["user_id"], r["day"])
        deltas = list(
            qs.filter(user_id=r["user_id"], created_at__date=r["day"])
              .values_list("delta_sec", flat=True)
        )
        active_map[key] = int(sum(min(int(x or 0), cap) for x in deltas))

    # --- имена и роли одним пакетом ---
    user_ids = sorted({r["user_id"] for r in rows if r.get("user_id")})

    users_by_id = {u.id: u for u in User.objects.filter(id__in=user_ids)}
    prof_by_uid = {p.user_id: p for p in UserProfile.objects.filter(user_id__in=user_ids)}

    enrols = Enrol.objects.filter(codigo=codigo, user_id__in=user_ids).values("user_id", "role")
    role_by_uid = {e["user_id"]: e["role"] for e in enrols}  # teacher/student

    out = []
    for r in rows:
        uid = r["user_id"]
        day = r["day"]
        u = users_by_id.get(uid)
        p = prof_by_uid.get(uid)

        role = role_by_uid.get(uid, "unknown")
        if role_q in ("student", "teacher") and role != role_q:
            continue

        out.append({
            "user_id": uid,
            "name": _display_name(u, p),
            "role": role,
            "day": (day.isoformat() if day else None),
            "events": int(r["events"] or 0),
            "active_sec": int(active_map.get((uid, day), int(r["active_sec"] or 0))),
            "first": (r["first"].isoformat() if r["first"] else None),
            "last": (r["last"].isoformat() if r["last"] else None),
        })

    return JsonResponse({
        "ok": True,
        "codigo": codigo,
        "range": {"from": (dfrom.isoformat() if dfrom else None), "to": (dto.isoformat() if dto else None)},
        "rows": out,
    })
