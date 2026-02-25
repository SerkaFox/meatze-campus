# shortshare/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404, FileResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import ShortRoom, ShortFile
from datetime import timedelta
import os
import mimetypes
import logging
from .realtime import push
logger = logging.getLogger(__name__)
from django.utils.http import http_date
from panel.preview_docx import ensure_docx_preview_pdf, preview_pdf_path_for
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
    payload = {
        "type": "file.created",
        "file": {
            "id": obj.id,
            "name": obj.original_name,
            "size": obj.size,
            "uploaded_at": int(obj.uploaded_at.timestamp()),
            "expires_at": int(obj.expires_at.timestamp()),
        }
    }
    push(room.code, payload)

    return JsonResponse({"ok": True, **payload["file"]})

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
    if pin != room.code:
        return JsonResponse({"ok": False, "error": "Contraseña incorrecta"}, status=403)

    obj = get_object_or_404(ShortFile, id=file_id, room=room)
    fid = obj.id   # <-- ВОТ ЭТО

    try:
        obj.file.delete(save=False)
    finally:
        obj.delete()

    push(room.code, {"type": "file.deleted", "id": fid})  # <-- А НЕ id()
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

    payload = {
        "type": "link.created",
        "link": {
            "id": obj.id,
            "url": obj.url,
            "title": obj.title,
            "created_at": int(obj.created_at.timestamp()),
            "expires_at": int(obj.expires_at.timestamp()),
        }
    }
    push(room.code, payload)

    return JsonResponse({"ok": True, **payload["link"]})

@require_POST
def delete_link(request, code, link_id: int):
    room = get_object_or_404(ShortRoom, code=code)
    pin = (request.POST.get("pin") or "").strip()
    if pin != room.code:
        return JsonResponse({"ok": False, "error": "Contraseña incorrecta"}, status=403)

    obj = get_object_or_404(ShortLink, id=link_id, room=room)
    lid = obj.id
    obj.delete()

    push(room.code, {"type": "link.deleted", "id": lid})
    return JsonResponse({"ok": True})
    
    
from django.views.decorators.clickjacking import xframe_options_sameorigin

@xframe_options_sameorigin
def view_file(request, code, file_id: int):
    room = get_object_or_404(ShortRoom, code=code)
    obj = get_object_or_404(ShortFile, id=file_id, room=room)
    if obj.expires_at <= timezone.now():
        raise Http404("Expired")

    name = obj.original_name or os.path.basename(obj.file.name or "file")
    ext = (name.rsplit(".", 1)[-1].lower() if "." in name else "")

    return render(request, "shortshare/viewer.html", {
        "room": room,
        "file": obj,
        "name": name,
        "ext": ext,
    })
    
import os
import mimetypes
import tempfile
import shutil
from pathlib import Path
from django.http import HttpResponse, FileResponse, Http404
from django.utils import timezone
from django.utils.http import http_date
from django.shortcuts import get_object_or_404

def inline_file(request, code, file_id: int):
    room = get_object_or_404(ShortRoom, code=code)
    obj = get_object_or_404(ShortFile, id=file_id, room=room)
    if obj.expires_at <= timezone.now():
        raise Http404("Expired")

    try:
        name = obj.original_name or os.path.basename(obj.file.name or "file")
        lower = name.lower()

        logger.warning("shortshare inline_file start id=%s path=%s name=%s",
                       obj.id, getattr(obj.file, "path", None), name)

        # DOCX -> PDF
        if lower.endswith(".docx"):
            from panel.preview_docx import ensure_docx_preview_pdf, preview_pdf_path_for

            # 1) копируем исходник в tmp с простым именем
            with tempfile.TemporaryDirectory(prefix="mz_ss_docx_") as d:
                d = Path(d)
                safe_src = d / "input.docx"

                with obj.file.open("rb") as src_fh:
                    with open(safe_src, "wb") as out_fh:
                        shutil.copyfileobj(src_fh, out_fh)

                logger.warning("shortshare safe copy ok: %s bytes=%s",
                               str(safe_src), safe_src.stat().st_size)

                # sanity: пустой файл
                if safe_src.stat().st_size < 100:
                    return HttpResponse("DOCX seems empty/corrupt", status=500)

                pdf_abs = ensure_docx_preview_pdf(str(safe_src), preview_pdf_path_for(obj.file))

            logger.warning("shortshare docx->pdf ok: %s size=%s",
                           pdf_abs, os.path.getsize(pdf_abs))

            resp = FileResponse(open(pdf_abs, "rb"), content_type="application/pdf")
            resp["Content-Disposition"] = 'inline; filename="preview.pdf"'
            resp["Last-Modified"] = http_date(os.path.getmtime(pdf_abs))
            resp["Cache-Control"] = "private, max-age=0, must-revalidate"
            return resp

        # PDF/images inline as-is
        ctype, _ = mimetypes.guess_type(name)
        ctype = ctype or "application/octet-stream"
        resp = FileResponse(obj.file.open("rb"), content_type=ctype)
        resp["Content-Disposition"] = f'inline; filename="{name}"'
        return resp

    except Exception as e:
        logger.exception("shortshare inline_file FAILED id=%s", file_id)
        return HttpResponse(f"Preview failed: {e}", status=500, content_type="text/plain")
        
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404

@require_POST
def extend_link(request, code, link_id: int):
    room = get_object_or_404(ShortRoom, code=code)

    pin = (request.POST.get("pin") or "").strip()
    if pin != room.code:
        return JsonResponse({"ok": False, "error": "Contraseña incorrecta"}, status=403)

    obj = get_object_or_404(ShortLink, id=link_id, room=room)

    # сколько прибавлять (минуты): 30 по умолчанию, или 1440 (= 1 día)
    try:
        mins = int(request.POST.get("mins") or "30")
    except ValueError:
        mins = 30

    # защита от треша
    if mins not in (30, 1440):
        return JsonResponse({"ok": False, "error": "mins_invalid"}, status=400)

    now = timezone.now()
    base = obj.expires_at if obj.expires_at and obj.expires_at > now else now
    obj.expires_at = base + timedelta(minutes=mins)
    obj.save(update_fields=["expires_at"])

    push(room.code, {
        "type": "link.extended",
        "id": obj.id,
        "expires_at": int(obj.expires_at.timestamp()),
        "mins": mins,
    })

    return JsonResponse({"ok": True, "expires_at": int(obj.expires_at.timestamp()), "mins": mins})