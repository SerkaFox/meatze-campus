import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q

from .models import Curso, CursoFolder, CursoFile


def _normalize_path(p):
    p = (p or "").strip().strip("/")
    return "/".join([x for x in p.split("/") if x])


def _leaf_name(path):
    path = _normalize_path(path)
    if not path:
        return ""
    return path.split("/")[-1]


def _join_path(*parts):
    out = []
    for p in parts:
        p = _normalize_path(p)
        if p:
            out.extend(p.split("/"))
    return "/".join(out)


@login_required
@require_POST
@transaction.atomic
def materiales_move_folder(request, codigo):

    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        return JsonResponse({"ok": False, "error": "curso_not_found"}, status=404)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "bad_json"}, status=400)

    source_path = _normalize_path(data.get("source_path"))
    target_parent = _normalize_path(data.get("target_parent"))

    if not source_path:
        return JsonResponse({"ok": False, "error": "missing_source"}, status=400)

    folder = CursoFolder.objects.filter(
        curso=curso,
        path=source_path,
        is_deleted=False
    ).first()

    if not folder:
        return JsonResponse({
            "ok": False,
            "error": "folder_not_found",
            "source_path": source_path,
            "target_parent": target_parent,
        }, status=404)

    if folder.is_locked:
        return JsonResponse({"ok": False, "error": "folder_locked"}, status=403)

    name = _leaf_name(source_path)
    new_path = _join_path(target_parent, name)

    if new_path == source_path:
        return JsonResponse({"ok": True})

    if target_parent.startswith(source_path):
        return JsonResponse({
            "ok": False,
            "error": "cannot_move_into_self",
            "message": "No se puede mover una carpeta dentro de una de sus subcarpetas."
        }, status=400)

    if CursoFolder.objects.filter(
        curso=curso,
        path=new_path,
        is_deleted=False
    ).exclude(pk=folder.pk).exists():
        return JsonResponse({"ok": False, "error": "name_conflict"}, status=409)

    old_prefix = source_path + "/"
    new_prefix = new_path + "/"

    folders = CursoFolder.objects.filter(
        curso=curso,
        is_deleted=False
    ).filter(
        Q(path=source_path) | Q(path__startswith=old_prefix)
    )

    for f in folders:

        if f.path == source_path:
            f.path = new_path
        else:
            tail = f.path[len(old_prefix):]
            f.path = new_prefix + tail

        f.save(update_fields=["path"])

    files = CursoFile.objects.filter(
        curso=curso
    ).filter(
        Q(folder_path=source_path) | Q(folder_path__startswith=old_prefix)
    )

    for cf in files:

        old = cf.folder_path or ""

        if old == source_path:
            cf.folder_path = new_path
        else:
            tail = old[len(old_prefix):]
            cf.folder_path = new_prefix + tail

        cf.save(update_fields=["folder_path"])

    return JsonResponse({
        "ok": True,
        "old_path": source_path,
        "new_path": new_path
    })