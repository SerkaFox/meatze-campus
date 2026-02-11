# panel/views_live.py
import re
import time
import jwt

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from api.models import Curso


def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "curso"


def _curso_room(curso) -> str:
    codigo = (getattr(curso, "codigo", "") or "").strip()
    base = codigo or f"curso-{getattr(curso, 'id', '')}"
    return f"meatze-{curso.id}-{_slug(base)}"


def _is_teacher_user(user) -> bool:
    if getattr(user, "is_teacher", False):
        return True
    try:
        return user.groups.filter(name__in=["Docentes", "Teachers", "Docente"]).exists()
    except Exception:
        return False


def _build_jitsi_jwt(*, room: str, user_name: str, is_teacher: bool) -> str | None:
    secret = getattr(settings, "JITSI_JWT_SECRET", "") or ""
    if not secret:
        return None

    domain = getattr(settings, "JITSI_DOMAIN", "meet.meatzeaula.es")
    app_id = getattr(settings, "JITSI_JWT_APP_ID", "meatze")
    aud = getattr(settings, "JITSI_JWT_AUD", "jitsi")
    ttl = int(getattr(settings, "JITSI_JWT_TTL_SECONDS", 2 * 60 * 60))

    now = int(time.time())

    user_ctx = {"name": user_name}
    if is_teacher:
        user_ctx.update({"moderator": True, "affiliation": "owner"})

    payload = {
        "aud": aud,
        "iss": app_id,
        "sub": domain,
        "room": room,
        "iat": now,
        "exp": now + ttl,
        "context": {"user": user_ctx},
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token.decode("utf-8") if isinstance(token, bytes) else token


def build_live_context(*, request, curso, is_teacher: bool) -> dict:
    domain = getattr(settings, "JITSI_DOMAIN", "meet.meatzeaula.es")
    display_name = (request.user.get_full_name() or request.user.username or "MEATZE").strip()
    room = _curso_room(curso)

    return {
        "jitsi_domain": domain,
        "jitsi_room": room,
        "jitsi_display_name": display_name,
        "jitsi_is_teacher": bool(is_teacher),
        "jitsi_jwt": _build_jitsi_jwt(room=room, user_name=display_name, is_teacher=bool(is_teacher)),
    }


@login_required
def curso_live(request, curso_id: int):
    curso = get_object_or_404(Curso, id=curso_id)
    is_teacher = _is_teacher_user(request.user)

    ctx = {"curso": curso}
    ctx.update(build_live_context(request=request, curso=curso, is_teacher=is_teacher))

    return render(request, "panel/curso_live.html", ctx)