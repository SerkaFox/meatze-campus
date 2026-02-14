# panel/views_modules_access.py
import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from api.models import Curso
from panel.models import StudentModuleAccess, CursoFolder

User = get_user_model()


def _user_is_teacher(user) -> bool:
    return bool(getattr(user, "is_teacher", False) or getattr(user, "is_staff", False))


def _course_modules(curso):
    # locked folders = модули
    locked = (CursoFolder.objects
              .filter(curso=curso, is_deleted=False, is_locked=True)
              .values("path", "title"))

    mods = []
    for x in locked:
        key = (x.get("path") or "").strip()                # стабильный ключ!
        if not key:
            continue
        label = (x.get("title") or "").strip() or key.split("/")[-1]
        mods.append({"key": key, "label": label})
    return mods

@csrf_exempt
@login_required
@require_GET
def teacher_student_modules_get(request):
    if not _user_is_teacher(request.user):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    codigo = (request.GET.get("codigo") or "").strip()
    alumno_id = (request.GET.get("alumno_id") or "").strip()
    if not codigo or not alumno_id:
        return JsonResponse({"ok": False, "error": "bad_request"}, status=400)

    curso = Curso.objects.filter(codigo=codigo).first()
    alumno = User.objects.filter(id=alumno_id).first()
    if not curso or not alumno:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)

    mods = _course_modules(curso)

    rows = (StudentModuleAccess.objects
            .filter(curso=curso, alumno=alumno)
            .values("module_key", "is_enabled"))

    state = {r["module_key"]: bool(r["is_enabled"]) for r in rows}

    items = [{
        "key": m["key"],
        "label": m["label"],
        "enabled": state.get(m["key"], True),
    } for m in mods]

    return JsonResponse({"ok": True, "items": items})


@csrf_exempt
@login_required
@require_POST
def teacher_student_modules_set(request):
    if not _user_is_teacher(request.user):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = {}

    codigo = (data.get("codigo") or "").strip()
    alumno_id = (data.get("alumno_id") or "").strip()
    items = data.get("items") or []

    curso = Curso.objects.filter(codigo=codigo).first()
    alumno = User.objects.filter(id=alumno_id).first()
    if not curso or not alumno:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)

    allowed_keys = {x["key"] for x in _course_modules(curso)}
    clean = []
    for x in items:
        k = (x.get("key") or "").strip()
        if not k or (allowed_keys and k not in allowed_keys):
            continue
        clean.append((k, bool(x.get("enabled", True))))

    with transaction.atomic():
        for k, en in clean:
            StudentModuleAccess.objects.update_or_create(
                curso=curso, alumno=alumno, module_key=k,
                defaults={"is_enabled": en}
            )

    return JsonResponse({"ok": True})
    
from panel.models import StudentModuleAccess, CursoFolder

def student_module_allowed(curso, alumno, module_key: str) -> bool:
    key = (module_key or "").strip()
    if not key:
        return True

    locked_keys = set(
        CursoFolder.objects
        .filter(curso=curso, is_deleted=False, is_locked=True)
        .values_list("path", flat=True)
    )
    if locked_keys and key not in locked_keys:
        return True

    row = (StudentModuleAccess.objects
           .filter(curso=curso, alumno=alumno, module_key=key)
           .only("is_enabled")
           .first())
    return True if row is None else bool(row.is_enabled)