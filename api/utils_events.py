import hashlib
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from django.db import transaction
from api.models import LearningEvent

import ipaddress

def _is_public_ip(s: str) -> bool:
    try:
        ip = ipaddress.ip_address(s)
        return ip.is_global
    except Exception:
        return False

def _client_ip(request):
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        # XFF может быть "client, proxy1, proxy2"
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        # берем первый глобальный; если нет — первый вообще
        for p in parts:
            if _is_public_ip(p):
                return p
        if parts:
            return parts[0]

    xr = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if xr:
        return xr

    return (request.META.get("REMOTE_ADDR") or "").strip()


def _safe_session_id(request, session_id: str | None):
    # если фронт не дал session_id, делаем стабильный хэш на основе django session + user agent
    sid = (session_id or "").strip()
    if sid:
        return sid[:64]
    base = (getattr(request, "session", None).session_key or "") + "|" + (request.META.get("HTTP_USER_AGENT") or "")
    if not base.strip():
        return ""
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]

def _parse_client_ts(ts_raw):
    # ts может прийти unix-ms или ISO
    if not ts_raw:
        return None
    try:
        if isinstance(ts_raw, (int, float)) or (isinstance(ts_raw, str) and ts_raw.isdigit()):
            ms = int(ts_raw)
            if ms > 10_000_000_000:  # ms
                return datetime.fromtimestamp(ms / 1000, tz=dt_timezone.utc)
            return datetime.fromtimestamp(ms, tz=dt_timezone.utc)
        # ISO
        return datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
    except Exception:
        return None

@transaction.atomic
def log_event(
    request,
    event: str,
    curso_codigo: str = "",
    object_type: str = "",
    object_id: str = "",
    meta: dict | None = None,
    session_id: str | None = None,
    seq: int | None = None,
    page: str = "",
    ref: str = "",
    client_ts=None,
):
    user = request.user
    if not user or not user.is_authenticated:
        return None

    sid = _safe_session_id(request, session_id)
    ip = _client_ip(request)
    ua = (request.META.get("HTTP_USER_AGENT") or "")[:255]

    client_dt = _parse_client_ts(client_ts)

    last = None
    if sid:
        last = (
            LearningEvent.objects
            .filter(user=user, session_id=sid)
            .order_by("-created_at")
            .first()
        )

    # Берём предыдущее событие этой же сессии (и курса, если он есть)
    qs = LearningEvent.objects.filter(user=user, session_id=sid)
    if curso_codigo:
        qs = qs.filter(curso_codigo=(curso_codigo or "")[:32])

    last = qs.order_by("-created_at").first()

    delta = 0
    if last:
        delta = int((timezone.now() - last.created_at).total_seconds())
        if delta < 0:
            delta = 0
        # cap 120s чтобы не накручивать активность при простое
        if delta > 120:
            delta = 120

        if seq is None:
            seq = (last.seq or 0) + 1

    if seq is None:
        seq = 1

    return LearningEvent.objects.create(
        curso_codigo=(curso_codigo or "")[:32],
        user=user,
        session_id=sid,
        seq=int(seq or 0),
        event=(event or "")[:50],
        object_type=(object_type or "")[:50],
        object_id=(str(object_id) or "")[:64],
        page=(page or "")[:200],
        ref=(ref or "")[:200],
        meta=meta or {},
        client_ts=client_dt,
        delta_sec=delta,
        ip=ip,
        user_agent=ua,
    )


from django.contrib.auth.models import User
from api.models import UserProfile  # если у тебя в api.models

def _display_name_for_user(user: User):
    if not user:
        return ""
    p = UserProfile.objects.filter(user=user).first()
    first = (p.first_name if p and p.first_name else user.first_name) or ""
    last1 = (p.last_name1 if p else "") or user.last_name or ""
    last2 = (p.last_name2 if p else "") or ""
    disp = (p.display_name if p and p.display_name else "") or ""
    # финальный приоритет
    name = (disp or f"{first} {last1} {last2}".strip() or user.get_full_name() or user.username or user.email or "")
    return " ".join(name.split())
