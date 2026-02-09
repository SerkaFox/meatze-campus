# panel/views_materiales_api.py
import os
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.core.files.base import ContentFile  # если надо, но для обычных файлов не нужно
from .models import CursoFile, CursoFolder
from .materiales_fs import normalize_path, create_folder  # у тебя уже есть
from api.models import Curso  # если нужно

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
    # ВАЖНО: вынеси это из course_panel (чтобы не было UnboundLocal)
    tp = (target_path or "").strip().strip("/")
    if not tp:
        return ""
    parts = tp.split("/")
    prefixes = []
    cur = ""
    for p in parts:
        cur = f"{cur}/{p}" if cur else p
        prefixes.append(cur)

    locked = (CursoFolder.objects
              .filter(curso=curso, is_deleted=False, is_locked=True, path__in=prefixes)
              .values("path", "title"))
    if not locked:
        return ""
    best = sorted(locked, key=lambda x: len(x["path"] or ""), reverse=True)[0]
    return (best.get("title") or "").strip() or best["path"].split("/")[-1]

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

    curso = Curso.objects.filter(code=course_code).first()
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
    
# panel/views_materiales_api.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def materiales_upload_folder_bundle(request):
    return JsonResponse({"ok": False, "error": "not_implemented"}, status=501)