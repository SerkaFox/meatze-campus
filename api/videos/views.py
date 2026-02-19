# app/videos/views.py
from django.shortcuts import render
from .models import Video

def mini_player(request):
    videos = list(Video.objects.filter(is_active=True).values(
        "id", "title", "url", "poster", "duration_sec"
    ))
    return render(request, "videos/mini_player.html", {"videos": videos})
    
# app/videos/views_api.py
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import get_object_or_404
from .models import Video
import os

def _can_manage(request) -> bool:
    # Настрой как нужно: staff / perms / teacher-role в MEATZE
    return request.user.is_authenticated and request.user.is_staff

@login_required
@require_http_methods(["GET"])
def api_list(request):
    qs = Video.objects.filter(is_active=True)
    data = [{
        "id": v.id,
        "title": v.title,
        "url": v.url,
        "poster": v.poster.url if v.poster else "",
        "duration_sec": 0,
    } for v in qs]
    return JsonResponse({"ok": True, "videos": data})

@login_required
@csrf_protect
@require_http_methods(["POST"])
def api_upload(request):
    if not _can_manage(request):
        return HttpResponseForbidden("nope")

    f = request.FILES.get("file")
    title = (request.POST.get("title") or "").strip()

    if not f:
        return HttpResponseBadRequest("file is required")
    if not title:
        title = os.path.splitext(f.name)[0]

    # Примитивная валидация
    ct = (getattr(f, "content_type", "") or "").lower()
    if not (ct.startswith("video/") or ct in {"application/octet-stream"}):
        return HttpResponseBadRequest("not a video")

    v = Video.objects.create(title=title, file=f, is_active=True)
    return JsonResponse({
        "ok": True,
        "video": {
            "id": v.id,
            "title": v.title,
            "url": v.url,
            "poster": "",
            "duration_sec": 0,
        }
    })

@login_required
@csrf_protect
@require_http_methods(["POST", "DELETE"])
def api_delete(request, video_id: int):
    if not _can_manage(request):
        return HttpResponseForbidden("nope")

    v = get_object_or_404(Video, id=video_id)

    # удалить файл с диска аккуратно
    if v.file:
        v.file.delete(save=False)
    if v.poster:
        v.poster.delete(save=False)

    v.delete()
    return JsonResponse({"ok": True})