import json
import posixpath
import zipfile
from django.core.files.base import ContentFile
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


def _parent_path(path):
    path = _normalize_path(path)
    if "/" not in path:
        return ""
    return path.rsplit("/", 1)[0]


def _user_is_teacher(user):
    return bool(
        getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
        or user.groups.filter(name="Docente").exists()
    )


def _clean_name(name):
    name = (name or "").strip().strip("/").replace("\\", "/")
    parts = [p.strip() for p in name.split("/") if p.strip()]
    return parts[-1] if parts else ""


def _copy_name(base):
    base = (base or "").strip()
    if not base:
        return "copia"
    return f"{base} - copia"


def _next_available_folder_path(curso, parent, desired_name):
    desired_name = _clean_name(desired_name)
    base = _copy_name(desired_name)
    candidate = _join_path(parent, base)
    idx = 2
    while CursoFolder.objects.filter(curso=curso, path=candidate, is_deleted=False).exists():
        candidate = _join_path(parent, f"{base} {idx}")
        idx += 1
    return candidate


def _infer_module_from_path(curso, target_path):
    target_path = _normalize_path(target_path)
    if not target_path:
        return ""

    prefixes = []
    acc = ""
    for part in target_path.split("/"):
        acc = f"{acc}/{part}" if acc else part
        prefixes.append(acc)

    locked = (
        CursoFolder.objects
        .filter(curso=curso, is_deleted=False, is_locked=True, path__in=prefixes)
        .values("path", "title")
    )
    if not locked:
        return ""

    best = sorted(locked, key=lambda x: len(x["path"] or ""), reverse=True)[0]
    return (best.get("title") or best["path"].split("/")[-1] or "").strip()


def _file_queryset_for_user(curso, user):
    qs = CursoFile.objects.filter(curso=curso)
    if not _user_is_teacher(user):
        return qs.none()
    return qs


def _ensure_folder_path(curso, path, user):
    path = _normalize_path(path)
    if not path:
        return None

    acc = ""
    obj = None
    for part in path.split("/"):
        acc = _join_path(acc, part)
        obj, _ = CursoFolder.objects.get_or_create(
            curso=curso,
            path=acc,
            defaults={
                "title": part,
                "created_by": user,
                "is_locked": False,
                "is_deleted": False,
            },
        )
        if obj.is_deleted:
            obj.is_deleted = False
            obj.save(update_fields=["is_deleted"])
    return obj


def _safe_zip_member_path(name):
    name = (name or "").replace("\\", "/")
    name = posixpath.normpath(name).strip("/")
    if not name or name == ".":
        return ""
    if name.startswith("../") or name == ".." or "/../" in name:
        return ""
    return _normalize_path(name)


def _archive_stem(name):
    name = _clean_name(name)
    if name.lower().endswith(".zip"):
        name = name[:-4]
    return name.strip() or "archivo"


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


@login_required
@require_POST
@transaction.atomic
def materiales_fs_op(request, codigo):
    if not _user_is_teacher(request.user):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        return JsonResponse({"ok": False, "error": "curso_not_found"}, status=404)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "bad_json"}, status=400)

    op = (data.get("op") or "").strip()
    audience = (data.get("audience") or "alumnos").strip()

    if op == "rename_file":
        file_id = data.get("file_id")
        name = _clean_name(data.get("name"))
        if not name:
            return JsonResponse({"ok": False, "error": "empty_name"}, status=400)

        cf = _file_queryset_for_user(curso, request.user).filter(pk=file_id).first()
        if not cf:
            return JsonResponse({"ok": False, "error": "file_not_found"}, status=404)

        cf.title = name[:255]
        cf.save(update_fields=["title"])
        return JsonResponse({
            "ok": True,
            "kind": "file",
            "file_id": cf.id,
            "name": cf.display_name,
        })

    if op == "rename_folder":
        source_path = _normalize_path(data.get("source_path"))
        new_name = _clean_name(data.get("name"))
        if not source_path or not new_name:
            return JsonResponse({"ok": False, "error": "bad_rename"}, status=400)

        folder = CursoFolder.objects.filter(curso=curso, path=source_path, is_deleted=False).first()
        if not folder:
            return JsonResponse({"ok": False, "error": "folder_not_found"}, status=404)
        if folder.is_locked:
            return JsonResponse({"ok": False, "error": "folder_locked"}, status=403)

        parent = _parent_path(source_path)
        new_path = _join_path(parent, new_name)
        if new_path != source_path and CursoFolder.objects.filter(
            curso=curso,
            path=new_path,
            is_deleted=False,
        ).exclude(pk=folder.pk).exists():
            return JsonResponse({"ok": False, "error": "name_conflict"}, status=409)

        old_prefix = source_path + "/"
        new_prefix = new_path + "/"

        folders = CursoFolder.objects.filter(curso=curso, is_deleted=False).filter(
            Q(path=source_path) | Q(path__startswith=old_prefix)
        )
        for f in folders:
            if f.path == source_path:
                f.path = new_path
                f.title = new_name
                f.save(update_fields=["path", "title"])
            else:
                tail = f.path[len(old_prefix):]
                f.path = new_prefix + tail
                f.save(update_fields=["path"])

        files = CursoFile.objects.filter(curso=curso).filter(
            Q(folder_path=source_path) | Q(folder_path__startswith=old_prefix)
        )
        for cf in files:
            old = cf.folder_path or ""
            if old == source_path:
                cf.folder_path = new_path
            else:
                tail = old[len(old_prefix):]
                cf.folder_path = new_prefix + tail
            cf.module_key = _infer_module_from_path(curso, cf.folder_path)
            cf.save(update_fields=["folder_path", "module_key"])

        return JsonResponse({
            "ok": True,
            "kind": "folder",
            "old_path": source_path,
            "new_path": new_path,
            "name": new_name,
        })

    if op == "copy_items":
        target_parent = _normalize_path(data.get("target_parent"))
        items = data.get("items") or []

        if target_parent and not CursoFolder.objects.filter(
            curso=curso,
            path=target_parent,
            is_deleted=False,
        ).exists():
            return JsonResponse({"ok": False, "error": "target_folder_not_found"}, status=404)

        created_files = []
        created_folders = []

        for item in items:
            kind = (item.get("kind") or "").strip()

            if kind == "file":
                cf = _file_queryset_for_user(curso, request.user).filter(pk=item.get("id")).first()
                if not cf:
                    continue
                new = CursoFile(
                    curso=curso,
                    uploaded_by=request.user,
                    tipo=cf.tipo,
                    module_key=_infer_module_from_path(curso, target_parent),
                    folder_path=target_parent,
                    title=cf.title,
                    file=cf.file,
                    size=cf.size,
                    ext=cf.ext,
                    share_alumnos=False,
                    is_visible_to_students=getattr(cf, "is_visible_to_students", False),
                )
                new.save()
                created_files.append(new.id)

            elif kind == "folder":
                source_path = _normalize_path(item.get("path"))
                src = CursoFolder.objects.filter(curso=curso, path=source_path, is_deleted=False).first()
                if not src:
                    continue
                if target_parent == source_path or target_parent.startswith(source_path + "/"):
                    return JsonResponse({"ok": False, "error": "cannot_copy_into_self"}, status=400)

                new_base_path = _next_available_folder_path(curso, target_parent, _leaf_name(source_path))
                source_prefix = source_path + "/"
                new_prefix = new_base_path + "/"

                src_folders = list(
                    CursoFolder.objects.filter(curso=curso, is_deleted=False).filter(
                        Q(path=source_path) | Q(path__startswith=source_prefix)
                    ).order_by("path")
                )
                for old_folder in src_folders:
                    if old_folder.path == source_path:
                        new_path = new_base_path
                    else:
                        new_path = new_prefix + old_folder.path[len(source_prefix):]

                    folder = CursoFolder.objects.create(
                        curso=curso,
                        path=new_path,
                        title=old_folder.title if old_folder.path != source_path else _leaf_name(new_base_path),
                        created_by=request.user,
                        is_locked=False,
                        is_deleted=False,
                    )
                    created_folders.append(folder.path)

                src_files = list(
                    _file_queryset_for_user(curso, request.user).filter(
                        Q(folder_path=source_path) | Q(folder_path__startswith=source_prefix)
                    )
                )
                for cf in src_files:
                    if cf.folder_path == source_path:
                        new_folder_path = new_base_path
                    else:
                        new_folder_path = new_prefix + cf.folder_path[len(source_prefix):]

                    new = CursoFile(
                        curso=curso,
                        uploaded_by=request.user,
                        tipo=cf.tipo,
                        module_key=_infer_module_from_path(curso, new_folder_path),
                        folder_path=new_folder_path,
                        title=cf.title,
                        file=cf.file,
                        size=cf.size,
                        ext=cf.ext,
                        share_alumnos=False,
                        is_visible_to_students=getattr(cf, "is_visible_to_students", False),
                    )
                    new.save()
                    created_files.append(new.id)

        return JsonResponse({
            "ok": True,
            "created_files": created_files,
            "created_folders": created_folders,
            "reload": True,
        })

    if op == "set_file_access":
        file_id = data.get("file_id")
        tipo = (data.get("tipo") or "").strip()
        share_alumnos = bool(data.get("share_alumnos"))

        if tipo not in {
            CursoFile.TIPO_ALUMNOS,
            CursoFile.TIPO_DOCENTES,
            CursoFile.TIPO_PRIVADO,
        }:
            return JsonResponse({"ok": False, "error": "bad_tipo"}, status=400)

        cf = _file_queryset_for_user(curso, request.user).filter(pk=file_id).first()
        if not cf:
            return JsonResponse({"ok": False, "error": "file_not_found"}, status=404)

        cf.tipo = tipo
        cf.share_alumnos = share_alumnos if tipo != CursoFile.TIPO_ALUMNOS else False
        if tipo == CursoFile.TIPO_PRIVADO:
            cf.uploaded_by = request.user
        cf.save(update_fields=["tipo", "share_alumnos", "uploaded_by"])

        return JsonResponse({
            "ok": True,
            "file_id": cf.id,
            "tipo": cf.tipo,
            "share_alumnos": bool(cf.share_alumnos),
        })

    if op == "set_folder_access":
        path = _normalize_path(data.get("path"))
        tipo = (data.get("tipo") or "").strip()
        share_alumnos = bool(data.get("share_alumnos"))
        recursive = bool(data.get("recursive", True))

        if tipo not in {
            CursoFile.TIPO_ALUMNOS,
            CursoFile.TIPO_DOCENTES,
            CursoFile.TIPO_PRIVADO,
        }:
            return JsonResponse({"ok": False, "error": "bad_tipo"}, status=400)

        if path:
            folder = CursoFolder.objects.filter(curso=curso, path=path, is_deleted=False).first()
            if not folder:
                return JsonResponse({"ok": False, "error": "folder_not_found"}, status=404)

        files = _file_queryset_for_user(curso, request.user)
        if path:
            if recursive:
                files = files.filter(Q(folder_path=path) | Q(folder_path__startswith=path + "/"))
            else:
                files = files.filter(folder_path=path)
        else:
            files = files.filter(folder_path="")

        update = {
            "tipo": tipo,
            "share_alumnos": share_alumnos if tipo != CursoFile.TIPO_ALUMNOS else False,
        }
        if tipo == CursoFile.TIPO_PRIVADO:
            update["uploaded_by"] = request.user

        count = files.update(**update)
        return JsonResponse({
            "ok": True,
            "path": path,
            "updated": count,
            "tipo": tipo,
            "share_alumnos": update["share_alumnos"],
        })

    if op == "zip_info":
        file_id = data.get("file_id")
        src = _file_queryset_for_user(curso, request.user).filter(pk=file_id).first()
        if not src:
            return JsonResponse({"ok": False, "error": "file_not_found"}, status=404)

        ext = (src.ext or "").lower().strip(".")
        filename = (src.filename or src.display_name or "").lower()
        if ext != "zip" and not filename.endswith(".zip"):
            return JsonResponse({"ok": False, "error": "not_zip"}, status=400)

        root_files = 0
        top_dirs = set()
        total_files = 0
        total_dirs = 0
        try:
            with src.file.open("rb") as fh:
                with zipfile.ZipFile(fh) as zf:
                    for member in zf.infolist():
                        rel = _safe_zip_member_path(member.filename)
                        if not rel:
                            continue
                        parts = rel.split("/")
                        if member.is_dir():
                            total_dirs += 1
                            if parts:
                                top_dirs.add(parts[0])
                            continue
                        total_files += 1
                        if len(parts) == 1:
                            root_files += 1
                        else:
                            top_dirs.add(parts[0])
        except zipfile.BadZipFile:
            return JsonResponse({"ok": False, "error": "bad_zip"}, status=400)

        return JsonResponse({
            "ok": True,
            "file_id": src.id,
            "archive_name": _archive_stem(src.display_name or src.filename),
            "root_files": root_files,
            "top_dirs": sorted(top_dirs),
            "top_dirs_count": len(top_dirs),
            "total_files": total_files,
            "total_dirs": total_dirs,
        })

    if op == "extract_zip_file":
        file_id = data.get("file_id")
        target_parent = _normalize_path(data.get("target_parent"))
        wrap_folder = bool(data.get("wrap_folder"))

        src = _file_queryset_for_user(curso, request.user).filter(pk=file_id).first()
        if not src:
            return JsonResponse({"ok": False, "error": "file_not_found"}, status=404)

        ext = (src.ext or "").lower().strip(".")
        filename = (src.filename or src.display_name or "").lower()
        if ext != "zip" and not filename.endswith(".zip"):
            return JsonResponse({"ok": False, "error": "not_zip"}, status=400)

        if target_parent and not CursoFolder.objects.filter(
            curso=curso,
            path=target_parent,
            is_deleted=False,
        ).exists():
            return JsonResponse({"ok": False, "error": "target_folder_not_found"}, status=404)

        if wrap_folder:
            target_parent = _join_path(target_parent, _archive_stem(src.display_name or src.filename))
            _ensure_folder_path(curso, target_parent, request.user)

        created_files = 0
        created_folders = set()

        try:
            with src.file.open("rb") as fh:
                with zipfile.ZipFile(fh) as zf:
                    members = zf.infolist()
                    for member in members:
                        rel = _safe_zip_member_path(member.filename)
                        if not rel:
                            continue

                        if member.is_dir():
                            folder_path = _join_path(target_parent, rel)
                            _ensure_folder_path(curso, folder_path, request.user)
                            created_folders.add(folder_path)
                            continue

                        if "/" in rel:
                            folder_rel, leaf = rel.rsplit("/", 1)
                        else:
                            folder_rel, leaf = "", rel
                        leaf = _clean_name(leaf)
                        if not leaf:
                            continue

                        folder_path = _join_path(target_parent, folder_rel)
                        if folder_path:
                            _ensure_folder_path(curso, folder_path, request.user)
                            created_folders.add(folder_path)

                        with zf.open(member, "r") as mf:
                            data_bytes = mf.read()

                        obj = CursoFile(
                            curso=curso,
                            uploaded_by=request.user,
                            tipo=src.tipo,
                            folder_path=folder_path,
                            module_key=_infer_module_from_path(curso, folder_path),
                            title=leaf,
                            size=len(data_bytes),
                            ext=(leaf.rsplit(".", 1)[-1].lower() if "." in leaf else ""),
                            share_alumnos=bool(src.share_alumnos),
                            is_visible_to_students=getattr(src, "is_visible_to_students", False),
                        )
                        obj.file.save(leaf, ContentFile(data_bytes), save=True)
                        created_files += 1
        except zipfile.BadZipFile:
            return JsonResponse({"ok": False, "error": "bad_zip"}, status=400)

        return JsonResponse({
            "ok": True,
            "file_id": src.id,
            "target_parent": target_parent,
            "created_files": created_files,
            "created_folders": len(created_folders),
            "reload": True,
        })

    return JsonResponse({"ok": False, "error": "bad_op"}, status=400)
