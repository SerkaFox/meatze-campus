# shortshare/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404, FileResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import ShortRoom, ShortFile
from datetime import timedelta

MAX_FILE_MB = 200
MAX_FILES_PER_ROOM = 50

def index(request):
    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()
        if not code.isdigit() or len(code) not in (2, 3, 4):
            return render(request, "shortshare/index.html", {"error": "Código inválido (2-4 dígitos)."})
        room, _ = ShortRoom.objects.get_or_create(code=code)
        return redirect("short_room", code=room.code)
    return render(request, "shortshare/index.html")

def room_view(request, code):
    room = get_object_or_404(ShortRoom, code=code)
    files = room.files.filter(expires_at__gt=timezone.now()).order_by("-uploaded_at")

    is_teacher = (request.GET.get("k") or "").strip() == (room.secret or "")

    return render(request, "shortshare/room.html", {
        "room": room,
        "files": files,
        "is_teacher": is_teacher,
    })

@csrf_exempt  # если ты делаешь отдельную “публичную” страницу вне общей CSRF-логики
@require_POST
def upload(request, code):
    room = get_object_or_404(ShortRoom, code=code)

    if room.files.filter(expires_at__gt=timezone.now()).count() >= MAX_FILES_PER_ROOM:
        return JsonResponse({"ok": False, "error": "Límite de archivos alcanzado."}, status=400)

    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"ok": False, "error": "No file."}, status=400)

    if f.size > MAX_FILE_MB * 1024 * 1024:
        return JsonResponse({"ok": False, "error": f"Archivo demasiado grande (máx {MAX_FILE_MB}MB)."}, status=400)

    obj = ShortFile.objects.create(
        room=room,
        file=f,
        original_name=f.name,
        size=f.size,
        expires_at=timezone.now() + timedelta(days=7),
    )
    return JsonResponse({
        "ok": True,
        "id": obj.id,
        "name": obj.original_name,
        "size": obj.size,
        "uploaded_at": int(obj.uploaded_at.timestamp()),
        "expires_at": int(obj.expires_at.timestamp()),
    })

def download(request, code, file_id: int):
    room = get_object_or_404(ShortRoom, code=code)
    obj = get_object_or_404(ShortFile, id=file_id, room=room)

    if obj.expires_at <= timezone.now():
        raise Http404("Expired")

    # FileResponse отдаст через X-Accel-Redirect можно ускорить (nginx), но и так ок
    resp = FileResponse(obj.file.open("rb"), as_attachment=True, filename=obj.original_name)
    return resp
    
from django.views.decorators.http import require_POST
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import ShortRoom, ShortFile

@require_POST
def delete_file(request, code, file_id: int):
    room = get_object_or_404(ShortRoom, code=code)

    pin = (request.POST.get("pin") or "").strip()

    # contraseña = código de la room
    if pin != room.code:
        return JsonResponse({"ok": False, "error": "Contraseña incorrecta"}, status=403)

    obj = get_object_or_404(ShortFile, id=file_id, room=room)

    try:
        obj.file.delete(save=False)
    finally:
        obj.delete()

    return JsonResponse({"ok": True})
    
# shortshare/views.py
import re
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from datetime import timedelta
from .models import ShortRoom, ShortFile, ShortLink

def room_view(request, code):
    room = get_object_or_404(ShortRoom, code=code)

    now = timezone.now()
    files = room.files.filter(expires_at__gt=now).order_by("-uploaded_at")
    links = room.links.filter(expires_at__gt=now).order_by("-created_at")

    is_teacher = (request.GET.get("k") or "").strip() == (room.secret or "")

    return render(request, "shortshare/room.html", {
        "room": room,
        "files": files,
        "links": links,
        "is_teacher": is_teacher,
    })

@require_POST
def add_link(request, code):
    room = get_object_or_404(ShortRoom, code=code)

    url = (request.POST.get("url") or "").strip()
    title = (request.POST.get("title") or "").strip()

    if not url:
        return JsonResponse({"ok": False, "error": "URL vacío."}, status=400)

    # чуть-чуть нормализации
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url

    # простая защита от мусора
    if len(url) > 1000:
        return JsonResponse({"ok": False, "error": "URL demasiado largo."}, status=400)

    obj = ShortLink.objects.create(
        room=room,
        url=url,
        title=title[:200],
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    return JsonResponse({
        "ok": True,
        "id": obj.id,
        "url": obj.url,
        "title": obj.title,
        "created_at": int(obj.created_at.timestamp()),
        "expires_at": int(obj.expires_at.timestamp()),
    })

@require_POST
def delete_link(request, code, link_id: int):
    room = get_object_or_404(ShortRoom, code=code)
    pin = (request.POST.get("pin") or "").strip()
    if pin != room.code:
        return JsonResponse({"ok": False, "error": "Contraseña incorrecta"}, status=403)

    obj = get_object_or_404(ShortLink, id=link_id, room=room)
    obj.delete()
    return JsonResponse({"ok": True})