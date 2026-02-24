# app/api/help_views.py
import re
import logging
from urllib.parse import unquote
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from api.videos.models import HelpBinding

log = logging.getLogger("meatze.help")

def _dbg_enabled(request):
    # включаем дебаг либо в DEBUG, либо вручную ?help_debug=1
    if getattr(settings, "DEBUG", False):
        return True
    return request.GET.get("help_debug") == "1"

def _role_from_request(request):
    if not request.user.is_authenticated:
        return "guest"

    prof = getattr(request.user, "profile", None)
    is_teacher = bool(prof and getattr(prof, "is_teacher", False))

    # если это staff/superuser, но он реальный преподаватель — считаем teacher
    if (request.user.is_staff or request.user.is_superuser) and is_teacher:
        return "teacher"

    # иначе чистый админ
    if request.user.is_staff or request.user.is_superuser:
        return "admin"

    if is_teacher:
        return "teacher"

    return "student"

def _match(binding_path: str, req_path: str) -> bool:
    binding_path = (binding_path or "").strip()
    req_path = (req_path or "").strip()
    if "*" not in binding_path:
        return binding_path == req_path
    esc = re.escape(binding_path).replace("\\*", ".*")
    return re.fullmatch(esc, req_path) is not None

@require_GET
def help_context(request):
    raw = unquote((request.GET.get("path", "") or "").strip())

    # raw может быть: "/alumno/curso/IFCT0309/?tab=materiales" или "/alumno/curso/IFCT0309/"
    if "?" in raw:
        req_path, req_query = raw.split("?", 1)
    else:
        req_path, req_query = raw, ""

    # ✅ query можно прислать отдельно (это важнее)
    separate_query = (request.GET.get("query", "") or "").strip()
    if separate_query:
        req_query = separate_query

    # ✅ ui (контекст UI: admin_mod:teachers, acc:pin_modal, etc.)
    raw_ui = (request.GET.get("ui", "") or "").strip()

    # ✅ общая строка матчинга для query_contains
    # (то, что мы ищем подстрокой)
    req_query_full = (req_query or "").strip()
    if raw_ui:
        req_query_full = (req_query_full + "&ui=" + raw_ui) if req_query_full else ("ui=" + raw_ui)

    role = _role_from_request(request)
    dbg = _dbg_enabled(request)

    if dbg:
        log.warning(
            "[help] user=%s auth=%s staff=%s super=%s prof.is_teacher=%s role=%s raw=%r path=%r query=%r ui=%r ua=%r",
            getattr(request.user, "id", None),
            request.user.is_authenticated,
            getattr(request.user, "is_staff", False),
            getattr(request.user, "is_superuser", False),
            getattr(getattr(request.user, "profile", None), "is_teacher", None),
            role, raw, req_path, req_query, raw_ui,
            request.META.get("HTTP_USER_AGENT", "")[:120],
        )

    def pick(role_name: str):
        qs = (HelpBinding.objects
              .select_related("playlist", "start_video")
              .filter(role=role_name, is_active=True)
              .order_by("-priority", "-id"))

        if dbg:
            log.warning("[help] scan role=%s candidates=%s", role_name, qs.count())

        for hb in qs:
            hp = (hb.path or "").strip()

            if not _match(hp, req_path.strip()):
                if dbg:
                    log.warning("[help] skip id=%s no-match hb.path=%r req_path=%r", hb.id, hp, req_path)
                continue

            qc = (hb.query_contains or "").strip()
            if qc and qc not in req_query_full:
                if dbg:
                    log.warning("[help] skip id=%s query-miss need=%r req_query_full=%r", hb.id, qc, req_query_full)
                continue

            if dbg:
                log.warning(
                    "[help] HIT id=%s role=%s title=%r path=%r query_contains=%r pl=%s token=%s start=%s",
                    hb.id, hb.role, hb.title, hb.path, hb.query_contains,
                    hb.playlist_id,
                    hb.playlist.share_token if hb.playlist else None,
                    hb.start_video_id
                )
            return hb

        return None

    best = pick(role)

    # fallback на guest
    if not best and role != "guest":
        best = pick("guest")

    if not best:
        if dbg:
            log.warning("[help] MISS role=%s path=%r query_full=%r", role, req_path, req_query_full)
        return JsonResponse({"ok": False, "role": role})

    pl = best.playlist
    token = pl.share_token

    embed_url = f"/videos/embed/{token}/?autoplay=1"
    if best.start_video_id:
        embed_url += f"&vid={best.start_video_id}"

    return JsonResponse({
        "ok": True,
        "embed_url": embed_url,
        "title": (best.title or pl.titulo or "Instrucción"),
        "role": role,
        "binding_id": best.id if dbg else None,
        "playlist_id": pl.id if dbg else None,
        "ui": raw_ui if dbg else None,
        "query_full": req_query_full if dbg else None,
    })