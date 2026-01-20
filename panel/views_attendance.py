# panel/views_attendance.py
from __future__ import annotations

import logging
import ipaddress
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from django.db import transaction

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.response import Response
from rest_framework import status

from api.models import Horario, Curso, Enrol, UserProfile
from panel.models import AttendanceSession  # <-- если AttendanceSession лежит в panel/models.py
# если AttendanceSession лежит в api.models, тогда замени на:
# from api.models import AttendanceSession

from api.utils_events import _safe_session_id

logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return
import ipaddress
from django.conf import settings

def _norm_ip(ip: str) -> str:
    return (ip or "").strip()

def _all_client_ips(request) -> list[str]:
    out: list[str] = []

    def add(ip: str):
        ip = _norm_ip(ip)
        if not ip:
            return
        try:
            ipaddress.ip_address(ip)
        except Exception:
            return
        if ip not in out:
            out.append(ip)

    xff = _norm_ip(request.META.get("HTTP_X_FORWARDED_FOR"))
    if xff:
        for p in xff.split(","):
            add(p)

    add(request.META.get("HTTP_X_REAL_IP"))
    add(request.META.get("REMOTE_ADDR"))
    return out

def _client_ip(request) -> str:
    ips = _all_client_ips(request)
    return ips[0] if ips else ""

def _lan_networks():
    cidrs = getattr(settings, "MZ_SCHOOL_LAN_CIDRS", None) or []
    nets = []
    for c in cidrs:
        try:
            nets.append(ipaddress.ip_network(str(c).strip(), strict=False))
        except Exception:
            continue
    return nets

def _is_school_lan_request(request) -> tuple[bool, dict]:
    ips = _all_client_ips(request)
    nets = _lan_networks()

    hit = None
    for ip in ips:
        try:
            addr = ipaddress.ip_address(ip)
        except Exception:
            continue
        for net in nets:
            if addr in net:
                hit = ip
                break
        if hit:
            break

    return (hit is not None), {
        "ips": ips,
        "lan_cidrs": [str(n) for n in nets],
        "hit": hit,
        "xff": request.META.get("HTTP_X_FORWARDED_FOR", ""),
        "xreal": request.META.get("HTTP_X_REAL_IP", ""),
        "remote": request.META.get("REMOTE_ADDR", ""),
    }



def _ua(request) -> str:
    return (request.META.get("HTTP_USER_AGENT") or "")[:255]


def _display_name(user):
    if not user:
        return ""
    p = UserProfile.objects.filter(user=user).first()
    disp = (getattr(p, "display_name", "") or "").strip() if p else ""
    if disp:
        return disp
    first = ((getattr(p, "first_name", "") if p else "") or user.first_name or "").strip()
    last1 = ((getattr(p, "last_name1", "") if p else "") or user.last_name or "").strip()
    last2 = ((getattr(p, "last_name2", "") if p else "") or "").strip()
    full = " ".join([x for x in [first, last1, last2] if x]).strip()
    return full or (user.get_full_name() or getattr(user, "email", "") or user.username or "").strip()


def _require_teacher(user, curso_codigo: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    return Enrol.objects.filter(codigo=curso_codigo, user=user, role="teacher").exists()


def _day_start(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _apply_slot_fields(obj: AttendanceSession, slot: Horario | None):
    obj.horario = slot
    obj.lesson_date = (slot.dia if slot else None)
    obj.lesson_start = (slot.hora_inicio if slot else None)
    obj.lesson_end = (slot.hora_fin if slot else None)


def _current_slot(curso: Curso, *, before_min=15, after_min=10):
    now = timezone.localtime()
    today = now.date()
    qs = Horario.objects.filter(curso=curso, dia=today).order_by("hora_inicio")
    for h in qs:
        start_dt = datetime.combine(today, h.hora_inicio, tzinfo=now.tzinfo) - timedelta(minutes=before_min)
        end_dt   = datetime.combine(today, h.hora_fin,    tzinfo=now.tzinfo) + timedelta(minutes=after_min)
        if start_dt <= now <= end_dt:
            return h
    return None


# ==========================================================
# 1) attendance_request
# ==========================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@transaction.atomic
def attendance_request(request):
    data = request.data or {}
    curso_codigo = (data.get("curso_codigo") or "").strip()[:32]
    if not curso_codigo:
        return Response({"ok": False, "error": "curso_codigo_required"}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    day_start = _day_start(now)

    ip = _client_ip(request)
    is_school, dbg_ip = _is_school_lan_request(request)

    logger.warning("ATT LAN school=%r hit=%r ips=%r",
                   is_school, dbg_ip.get("hit"), dbg_ip.get("ips"))

    new_status = AttendanceSession.STATUS_PENDING if is_school else AttendanceSession.STATUS_OFFSITE


    ua = _ua(request)
    sid = _safe_session_id(request, (data.get("session_id") or "").strip()[:64])


    curso = Curso.objects.filter(codigo=curso_codigo).first()
    slot = _current_slot(curso) if curso else None

    obj = (AttendanceSession.objects
           .select_for_update()
           .filter(user=request.user, curso_codigo=curso_codigo, started_at__gte=day_start)
           .exclude(status=AttendanceSession.STATUS_ENDED)
           .order_by("-started_at", "-id")
           .first())

    if not obj:
        obj = AttendanceSession.objects.create(
            curso_codigo=curso_codigo,
            user=request.user,
            status=AttendanceSession.STATUS_PENDING if is_school else AttendanceSession.STATUS_OFFSITE,
            ip=ip,
            user_agent=ua,
            session_id=sid,
        )
        _apply_slot_fields(obj, slot)
        obj.last_seen_at = now
        obj.last_heartbeat_at = now
        obj.save(update_fields=[
            "horario","lesson_date","lesson_start","lesson_end",
            "last_seen_at","last_heartbeat_at"
        ])
    else:
        obj.ip = ip
        obj.user_agent = ua
        if sid:
            obj.session_id = sid

        # обновляем слот (если нашли текущий)
        if slot and obj.horario_id != slot.id:
            _apply_slot_fields(obj, slot)

        # статус меняем только если ещё не CONFIRMED
        if obj.status in (AttendanceSession.STATUS_PENDING,
                          AttendanceSession.STATUS_OFFSITE,
                          AttendanceSession.STATUS_REJECTED):
            obj.status = AttendanceSession.STATUS_PENDING if is_school else AttendanceSession.STATUS_OFFSITE

        obj.last_seen_at = now
        obj.last_heartbeat_at = now
        obj.save(update_fields=[
            "ip","user_agent","session_id","status",
            "horario","lesson_date","lesson_start","lesson_end",
            "last_seen_at","last_heartbeat_at"
        ])

    return Response({
        "ok": True,
        "curso_codigo": curso_codigo,
        "status": obj.status,
        "is_school_ip": is_school,
        "id": obj.id,
        "slot_id": obj.horario_id,
        "dbg": {
            "ip": ip,
            "want": (getattr(settings, "MZ_SCHOOL_PUBLIC_IP", "") or "").strip(),
            "wants": getattr(settings, "MZ_SCHOOL_PUBLIC_IPS", None),
            "xff": request.META.get("HTTP_X_FORWARDED_FOR", ""),
            "xreal": request.META.get("HTTP_X_REAL_IP", ""),
            "remote": request.META.get("REMOTE_ADDR", ""),
        }
    })


# ==========================================================
# 2) attendance_heartbeat
# ==========================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@transaction.atomic
def attendance_heartbeat(request):
    data = request.data or {}
    curso_codigo = (data.get("curso_codigo") or "").strip()[:32]
    if not curso_codigo:
        return Response({"ok": False, "error": "curso_codigo_required"}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    day_start = _day_start(now)

    ip = _client_ip(request)
    is_school, dbg_ip = _is_school_lan_request(request)


    # поля

    ua = _ua(request)
    sid = _safe_session_id(request, (data.get("session_id") or "").strip()[:64])
    

    curso = Curso.objects.filter(codigo=curso_codigo).first()
    slot = _current_slot(curso) if curso else None

    obj = (AttendanceSession.objects
           .select_for_update()
           .filter(user=request.user, curso_codigo=curso_codigo, started_at__gte=day_start)
           .exclude(status=AttendanceSession.STATUS_ENDED)
           .order_by("-started_at", "-id")
           .first())

    if not obj:
        obj = AttendanceSession.objects.create(
            curso_codigo=curso_codigo,
            user=request.user,
            status=AttendanceSession.STATUS_PENDING if is_school else AttendanceSession.STATUS_OFFSITE,
            ip=ip,
            user_agent=ua,
            session_id=sid,
        )
        _apply_slot_fields(obj, slot)
        obj.last_seen_at = now
        obj.last_heartbeat_at = now
        obj.save(update_fields=[
            "horario","lesson_date","lesson_start","lesson_end",
            "last_seen_at","last_heartbeat_at"
        ])
    else:
        # ✅ статус по сети меняем только если ещё не CONFIRMED
        if obj.status in (AttendanceSession.STATUS_PENDING,
                          AttendanceSession.STATUS_OFFSITE,
                          AttendanceSession.STATUS_REJECTED):
            obj.status = AttendanceSession.STATUS_PENDING if is_school else AttendanceSession.STATUS_OFFSITE


    # завершение урока по lesson_end (если известно)
    if obj.lesson_date and obj.lesson_end:
        end_dt = timezone.make_aware(datetime.combine(obj.lesson_date, obj.lesson_end))
        if now > end_dt + timedelta(minutes=10):
            obj.status = AttendanceSession.STATUS_ENDED
            obj.ended_at = now
            obj.ip = ip
            obj.last_heartbeat_at = now
            obj.save(update_fields=["status", "ended_at", "ip", "last_heartbeat_at"])
            return Response({"ok": True, "status": obj.status, "ended": True, "reason": "lesson_finished"})

    # delta активности
    delta = 0
    if obj.last_seen_at:
        delta = int((now - obj.last_seen_at).total_seconds())
        if delta < 0:
            delta = 0
        if delta > 120:
            delta = 120

    obj.active_sec = int(obj.active_sec or 0) + delta
    if obj.status == AttendanceSession.STATUS_CONFIRMED:
        obj.active_confirmed_sec = int(obj.active_confirmed_sec or 0) + delta

    # техполя
    obj.ip = ip
    obj.user_agent = ua
    if sid:
        obj.session_id = sid

    # слот обновить, если нашли
    if slot and obj.horario_id != slot.id:
        _apply_slot_fields(obj, slot)

    obj.last_seen_at = now
    obj.last_heartbeat_at = now
    obj.save(update_fields=[
        "status",
        "ip","user_agent","session_id",
        "horario","lesson_date","lesson_start","lesson_end",
        "active_sec","active_confirmed_sec",
        "last_seen_at","last_heartbeat_at"
    ])

    return Response({
        "ok": True,
        "curso_codigo": curso_codigo,
        "status": obj.status,
        "is_school_ip": is_school,
        "id": obj.id,
        "slot_id": obj.horario_id,
        "dbg": {
            "ip": ip,
            "lan": dbg_ip,
            "want": (getattr(settings, "MZ_SCHOOL_PUBLIC_IP", "") or "").strip(),
            "wants": getattr(settings, "MZ_SCHOOL_PUBLIC_IPS", None),
            "xff": request.META.get("HTTP_X_FORWARDED_FOR", ""),
            "xreal": request.META.get("HTTP_X_REAL_IP", ""),
            "remote": request.META.get("REMOTE_ADDR", ""),
        }
    })


# ==========================================================
# 3) teacher_attendance_pending  (ВОТ ЕЁ НЕ ХВАТАЛО)
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def teacher_attendance_pending(request):
    curso_codigo = (request.GET.get("course_code") or request.GET.get("curso_codigo") or "").strip()[:32]
    if not curso_codigo:
        return Response({"ok": False, "error": "curso_codigo_required"}, status=status.HTTP_400_BAD_REQUEST)

    if not _require_teacher(request.user, curso_codigo):
        return Response({"ok": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    hb_sec = int(getattr(settings, "MZ_ATTENDANCE_HB_SEC", 90) or 90)
    now = timezone.now()
    day_start = _day_start(now)

    qs = (AttendanceSession.objects
          .filter(curso_codigo=curso_codigo,
                  status=AttendanceSession.STATUS_PENDING,
                  started_at__gte=day_start)
          .order_by("started_at")[:200]
          .select_related("user"))

    items = []
    for a in qs:
        items.append({
            "id": a.id,
            "user_id": a.user_id,
            "name": _display_name(a.user),
            "started_at": a.started_at.isoformat(),
            "ip": a.ip,
            "alive": a.is_alive(hb_sec),
        })

    return Response({"ok": True, "curso_codigo": curso_codigo, "items": items})


# ==========================================================
# 4) teacher_attendance_decide (можно пере-решать)
# ==========================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@transaction.atomic
def teacher_attendance_decide(request):
    data = request.data or {}
    curso_codigo = (data.get("curso_codigo") or "").strip()[:32]
    decision = (data.get("decision") or "").strip().lower()
    aid = data.get("attendance_id")

    if not curso_codigo or not aid or decision not in ("confirm", "reject"):
        return Response({"ok": False, "error": "bad_request"}, status=status.HTTP_400_BAD_REQUEST)

    if not _require_teacher(request.user, curso_codigo):
        return Response({"ok": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    obj = AttendanceSession.objects.select_for_update().filter(id=aid, curso_codigo=curso_codigo).first()
    if not obj:
        return Response({"ok": False, "error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    if obj.status == AttendanceSession.STATUS_ENDED:
        return Response({"ok": False, "error": "ended"}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    obj.teacher = request.user
    obj.decided_at = now

    if decision == "confirm":
        obj.status = AttendanceSession.STATUS_CONFIRMED
        obj.confirmed_at = now  # можно и "obj.confirmed_at or now", но для re-confirm логичнее обновлять
        obj.last_heartbeat_at = now
    else:
        obj.status = AttendanceSession.STATUS_REJECTED
        # если хочешь, чтобы после reject “явка” считалась не подтвержденной:
        obj.confirmed_at = None

    obj.save(update_fields=["teacher", "decided_at", "status", "confirmed_at", "last_heartbeat_at"])
    return Response({"ok": True, "id": obj.id, "status": obj.status, "user_id": obj.user_id})
