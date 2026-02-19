# panel/views_materiales_api.py
import os
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.core.files.base import ContentFile  
from django.db.models import Q
from .models import CursoFile, CursoFolder
from .materiales_fs import normalize_path, create_folder  # у тебя уже есть
from api.models import Curso  # если нужно
from panel.permissions_modules import get_disabled_modules

def _fmt_size(num):
    try:
        n = float(num or 0)
    except (TypeError, ValueError):
        n = 0.0
    for unit in ("B","KB","MB","GB","TB"):
        if n < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n} B"

def _infer_module_from_path(curso, target_path: str) -> str:
    # возвращает КЛЮЧ МОДУЛЯ = locked folder PATH (стабильный ключ)
    tp = (target_path or "").strip().strip("/")
    if not tp:
        return ""

    parts = tp.split("/")
    prefixes = []
    cur = ""
    for p in parts:
        cur = f"{cur}/{p}" if cur else p
        prefixes.append(cur)

    locked_paths = list(
        CursoFolder.objects
            .filter(curso=curso, is_deleted=False, is_locked=True, path__in=prefixes)
            .values_list("path", flat=True)
    )
    if not locked_paths:
        return ""

    # самый глубокий locked path
    locked_paths.sort(key=len, reverse=True)
    return locked_paths[0]

@login_required
@require_POST
def materiales_upload_files_ajax(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "auth_required"}, status=401)

    # ✅ идентифицируй курс как у тебя принято:
    # вариант А: курс в URL /alumno/curso/<slug>/...
    # вариант Б: курс в POST, или в session
    # Я сделаю универсально: ждем course_code в POST, иначе 400
    course_code = (request.POST.get("course_code") or "").strip()
    if not course_code:
        return JsonResponse({"ok": False, "error": "course_code_required"}, status=400)

    curso = Curso.objects.filter(codigo=course_code).first()
    if not curso:
        return JsonResponse({"ok": False, "error": "curso_not_found"}, status=404)

    # ✅ проверь teacher (как у тебя делается is_teacher)
    # если у тебя is_teacher вычисляется в course_panel — вынеси в helper
    is_teacher = True  # TODO: replace with real check
    if not is_teacher:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    folder_path = normalize_path(request.POST.get("folder_path") or "")
    files = request.FILES.getlist("files")
    if not files:
        return JsonResponse({"ok": False, "error": "no_files"}, status=400)

    created = []
    for f in files:
        obj = CursoFile(
            curso=curso,
            uploaded_by=request.user,
            tipo=CursoFile.TIPO_ALUMNOS,  # или подай tipo отдельным полем
            folder_path=folder_path,
            module_key=_infer_module_from_path(curso, folder_path),
            title=f.name,
            size=f.size,
            ext=(f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""),
        )
        obj.file = f
        obj.save()

        # если твой partial для дерева называется иначе — поменяй
        obj.fmt_size = _fmt_size(obj.size)

        file_html = render_to_string(
            "panel/partials/materiales_tree_file.html",
            {"f": obj, "is_teacher": True},
            request=request,
        )

        created.append({"id": obj.id, "file_html": file_html})

    return JsonResponse({"ok": True, "folder_path": folder_path, "files": created})
    

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def materiales_upload_folder_bundle(request):
    return JsonResponse({"ok": False, "error": "not_implemented"}, status=501)
    
import io
import re
import zipfile
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify

from api.models import Curso
from .models import CursoFile, MaterialDownload

def _safe_zip_name(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    return s[:120] or "materiales"

def _tipo_from_audience(aud: str) -> str:
    aud = (aud or "").strip().lower()
    if aud == "docentes":
        return getattr(CursoFile, "TIPO_DOCENTES", "docentes")
    if aud == "mis":
        return getattr(CursoFile, "TIPO_PRIVADO", "privado")
    return getattr(CursoFile, "TIPO_ALUMNOS", "alumnos")

def _user_is_teacher(user) -> bool:
    # подставь свой реальный чек
    return bool(getattr(user, "is_teacher", False) or getattr(user, "is_staff", False))

@login_required
@require_GET
def materiales_download_zip(request):
    """
    GET /panel/materiales/zip/?codigo=IFCT0309&aud=alumnos&p=A/B&scope=folder
    scope: folder | all
    """
    codigo = (request.GET.get("codigo") or "").strip()
    if not codigo:
        return JsonResponse({"ok": False, "error": "codigo_required"}, status=400)

    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        return JsonResponse({"ok": False, "error": "curso_not_found"}, status=404)

    aud = (request.GET.get("aud") or "alumnos").strip().lower()
    scope = (request.GET.get("scope") or "folder").strip().lower()
    folder_path = (request.GET.get("p") or "").strip().strip("/")  # "A/B"

    is_teacher = _user_is_teacher(request.user)

    qs = CursoFile.objects.filter(curso=curso)

    # удалённые
    if hasattr(CursoFile, "is_deleted"):
        qs = qs.filter(is_deleted=False)

    if is_teacher:
        # учитель: по выбранной аудитории
        tipo = _tipo_from_audience(aud)
        qs = qs.filter(tipo=tipo)

    else:
        # ученик: только то, что ему видно
        if hasattr(CursoFile, "share_alumnos"):
            qs = qs.filter(Q(tipo=_tipo_from_audience("alumnos")) | Q(share_alumnos=True))
        else:
            qs = qs.filter(tipo=_tipo_from_audience("alumnos"))

        # и минус запрещённые модули
        disabled = get_disabled_modules(curso, request.user)
        if disabled:
            qs = qs.exclude(module_key__in=list(disabled))
        
    # scope
    if scope == "all":
        pass
    else:
        # folder-only (включая подпапки)
        if folder_path:
            qs = qs.filter(folder_path__startswith=folder_path)
        else:
            # root: только файлы в корне (folder_path пустой)
            qs = qs.filter(folder_path="")

    files = list(qs.select_related("uploaded_by"))
    if not files:
        return JsonResponse({"ok": False, "error": "no_files"}, status=404)

    # ---------- build zip in memory ----------
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in files:
            # arcname
            fp = (getattr(f, "folder_path", "") or "").strip().strip("/")
            base = (f.display_name if hasattr(f, "display_name") else "") or getattr(f, "title", "") or getattr(f, "filename", "") or "file"
            base = _safe_zip_name(base)

            ext = getattr(f, "ext", "") or ""
            if ext and not base.lower().endswith("." + ext.lower()):
                base = f"{base}.{ext}"

            if scope == "all":
                arc = f"{fp}/{base}" if fp else base
            else:
                # folder scope: делаем путь относительно выбранной папки
                if folder_path and fp.startswith(folder_path):
                    rel = fp[len(folder_path):].lstrip("/")
                    arc = f"{rel}/{base}" if rel else base
                else:
                    arc = base

            # write file
            # (если у тебя FileField локальный, это работает)
            try:
                with f.file.open("rb") as fh:
                    z.writestr(arc, fh.read())
            except Exception:
                # если файл недоступен — пропускаем, но можно и падать
                continue

    buf.seek(0)

    # ---------- mark downloads for alumno ----------
    if not is_teacher:
        ip = request.META.get("REMOTE_ADDR")
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:255]

        rows = [
            MaterialDownload(file_id=f.id, alumno=request.user, ip=ip, user_agent=ua)
            for f in files
        ]
        # уникальность на (file, alumno) — используем ignore_conflicts
        MaterialDownload.objects.bulk_create(rows, ignore_conflicts=True)

    # filename
    part = "ALL" if scope == "all" else (folder_path or "RAIZ")
    out_name = f"{curso.codigo}_{aud}_{part}.zip"
    out_name = _safe_zip_name(out_name)

    resp = HttpResponse(buf.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="{out_name}"'
    return resp
    
from django.http import FileResponse, Http404
from django.utils.http import http_date
import mimetypes
import os


def _is_docx(name: str) -> bool:
    return (name or "").lower().endswith(".docx")

@login_required
def materiales_file(request, file_id: int):
    cf = get_object_or_404(CursoFile, pk=file_id)

    # твоя проверка прав (сейчас она уже есть для скачивания)
    if not user_can_access_file(request.user, cf):
        # если у тебя check=1 возвращает JSON — сохрани текущую логику
        raise Http404()

    inline = request.GET.get("inline") == "1"

    # --- ВОТ НОВОЕ: docx preview через pdf ---
    if inline and _is_docx(cf.file.name):
        pdf_abs = ensure_docx_preview_pdf(
            cf.file.path,
            preview_pdf_path_for_filefield(cf.file),
        )
        f = open(pdf_abs, "rb")
        resp = FileResponse(f, content_type="application/pdf")
        resp["Content-Disposition"] = 'inline; filename="preview.pdf"'
        resp["Cache-Control"] = "private, max-age=0, must-revalidate"
        resp["Last-Modified"] = http_date(os.path.getmtime(pdf_abs))
        return resp

    # --- остальное: как было (pdf/img/обычная скачка) ---
    content_type = cf.mime or mimetypes.guess_type(cf.file.name)[0] or "application/octet-stream"
    resp = FileResponse(cf.file.open("rb"), content_type=content_type)

    if inline:
        resp["Content-Disposition"] = f'inline; filename="{os.path.basename(cf.file.name)}"'
    else:
        resp["Content-Disposition"] = f'attachment; filename="{os.path.basename(cf.file.name)}"'

    return resp