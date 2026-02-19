# panel/views_live.py
import re
import time
import jwt

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from api.models import Curso
import logging
logger = logging.getLogger("jitsi")

def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "curso"


from django.utils import timezone

from django.utils import timezone

def _curso_room(curso) -> str:
    codigo = (curso.codigo or "").strip()

    today = timezone.localdate()
    date_str = today.strftime("%d%b%Y").lower()  # 18feb2026

    base = f"{codigo}-{date_str}".strip("-")

    return f"curso-{_slug(base)}"

def _is_teacher_user(user) -> bool:
    # 0) суперюзер
    if getattr(user, "is_superuser", False):
        return True

    # 1) profile.is_teacher
    prof = getattr(user, "profile", None)
    if prof and getattr(prof, "is_teacher", False):
        return True

    # 2) группа
    try:
        return user.groups.filter(name__in=["Docentes", "Teachers", "Docente"]).exists()
    except Exception:
        return False


def _build_jitsi_jwt(*, room: str, user_name: str, is_teacher: bool) -> str | None:
    if not getattr(settings, "JITSI_JWT_ENABLED", False):
        return None

    # ❗ JWT ТОЛЬКО ДЛЯ УЧИТЕЛЯ
    if not is_teacher:
        return None

    secret = getattr(settings, "JITSI_JWT_SECRET", "") or ""
    if not secret:
        return None

    domain = getattr(settings, "JITSI_DOMAIN", "meetjwt.meatzeaula.es")
    app_id = getattr(settings, "JITSI_JWT_APP_ID", "meatze")
    aud = getattr(settings, "JITSI_JWT_AUD", "jitsi")
    ttl = int(getattr(settings, "JITSI_JWT_TTL_SECONDS", 2 * 60 * 60))

    now = int(time.time())

    payload = {
      "aud": aud,
      "iss": app_id,
      "sub": domain,
      "room": room,
      "iat": now,
      "exp": now + ttl,
      "context": {
        "user": {
          "name": user_name,
          "affiliation": "owner",
          "moderator": True,
        }
      },
    }
    token = jwt.encode(payload, secret, algorithm="HS256")

    # Логируем только payload + длину токена
    logger.warning("JITSI_JWT gen: is_teacher=%s room=%s aud=%s iss=%s sub=%s moderator=%s exp=%s token_len=%s",
                   is_teacher, room, payload.get("aud"), payload.get("iss"), payload.get("sub"),
                   payload["context"]["user"].get("moderator"), payload.get("exp"), len(token))
    return token


def build_live_context(*, request, curso, is_teacher: bool) -> dict:
    domain = getattr(settings, "JITSI_DOMAIN", "meetjwt.meatzeaula.es")  # <-- ВАЖНО
    display_name = (request.user.get_full_name() or request.user.username or "MEATZE").strip()
    room = _curso_room(curso)

    token = _build_jitsi_jwt(
        room=room,
        user_name=display_name,
        is_teacher=bool(is_teacher),
    )

    return {
        "jitsi_domain": domain,
        "jitsi_room": room,
        "jitsi_display_name": display_name,
        "jitsi_is_teacher": bool(is_teacher),
        "jitsi_jwt": token,
    }
from django.views.decorators.csrf import ensure_csrf_cookie
@ensure_csrf_cookie
@login_required
def curso_live(request, curso_id: int):
    curso = get_object_or_404(Curso, id=curso_id)
    is_teacher = _is_teacher_user(request.user)

    ctx = {
      "curso": curso,
      "is_teacher": bool(is_teacher),
      "live_is_open": bool(getattr(curso, "live_is_open", False)),
    }
    ctx.update(build_live_context(request=request, curso=curso, is_teacher=is_teacher))
    return render(request, "panel/curso_live.html", ctx)
    
    
# panel/views_live.py
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

LIVE_TIMEOUT_SECONDS = 60

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_POST
@login_required
def curso_live_ping(request, curso_id: int):
    logger.warning("LIVE_PING HIT: user=%s id=%s path=%s", request.user.username, request.user.id, request.path)
    curso = get_object_or_404(Curso, id=curso_id)
    logger.warning("PING user=%s id=%s groups=%s profile_teacher=%s user_is_teacher_attr=%s",
        request.user.username,
        request.user.id,
        list(request.user.groups.values_list("name", flat=True)),
        getattr(getattr(request.user, "profile", None), "is_teacher", None),
        getattr(request.user, "is_teacher", None),
    )
    if not _is_teacher_user(request.user):
        logger.warning("LIVE_PING TEACHER CHECK FAIL: user=%s groups=%s is_teacher_attr=%s",
               request.user.username,
               list(request.user.groups.values_list("name", flat=True)),
               getattr(request.user, "is_teacher", None))
        return HttpResponseForbidden("Only teachers")

    now = timezone.now()
    if not curso.live_is_open:
        curso.live_is_open = True
        curso.live_opened_at = now
        curso.live_closed_at = None
    curso.live_last_signal_at = now
    curso.save(update_fields=["live_is_open", "live_opened_at", "live_closed_at", "live_last_signal_at"])
    return JsonResponse({"ok": True, "open": True})

@csrf_exempt
@require_POST
@login_required
def curso_live_close(request, curso_id: int):
    curso = get_object_or_404(Curso, id=curso_id)
    if not _is_teacher_user(request.user):
        return HttpResponseForbidden("Only teachers")

    now = timezone.now()
    curso.live_is_open = False
    curso.live_closed_at = now
    curso.live_last_signal_at = now
    curso.save(update_fields=["live_is_open", "live_closed_at", "live_last_signal_at"])
    return JsonResponse({"ok": True, "open": False})

@login_required
def curso_live_status(request, curso_id: int):
    curso = get_object_or_404(Curso, id=curso_id)

    # страховка: если учитель пропал, считаем эфир закрытым
    now = timezone.now()
    last = curso.live_last_signal_at
    if curso.live_is_open and last and (now - last).total_seconds() > LIVE_TIMEOUT_SECONDS:
        curso.live_is_open = False
        curso.live_closed_at = now
        curso.save(update_fields=["live_is_open", "live_closed_at"])

    return JsonResponse({"open": bool(curso.live_is_open)})
    


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from api.models import Curso, Enrol

@login_required
def curso_live_popup(request, codigo: str):
    curso = get_object_or_404(Curso, codigo=codigo)
    is_teacher = _is_teacher_user(request.user)  # или через Enrol, как хочешь

    ctx = {"curso": curso, "is_teacher": bool(is_teacher)}
    ctx.update(build_live_context(request=request, curso=curso, is_teacher=bool(is_teacher)))
    return render(request, "panel/live_popup.html", ctx)