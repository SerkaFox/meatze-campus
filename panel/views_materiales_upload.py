import json
import os
import shutil
from urllib.parse import quote
import uuid
from pathlib import Path
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .decorators import require_profile_complete
from .models import CursoFile, CursoFolder
from api.models import Curso, Enrol
from .materiales_fs import normalize_path, create_folder
GOOGLE_DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
def _normalize_path(p: str) -> str:
    p = (p or "").strip().replace("\\", "/").strip("/")
    while "//" in p:
        p = p.replace("//", "/")
    return p


def _safe_name(name: str, max_base_len: int = 80) -> str:
    name = (name or "file").strip().replace("\\", "_").replace("/", "_")

    # чуть чистим проблемные символы
    name = "".join(
        ch if ch.isalnum() or ch in "._- ()" else "_"
        for ch in name
    ).strip(" ._")

    if not name:
        name = "file"

    if "." in name:
        base, ext = name.rsplit(".", 1)
        ext = ext[:10].lower()
    else:
        base, ext = name, ""

    base = base[:max_base_len].strip(" ._")
    if not base:
        base = "file"

    return f"{base}.{ext}" if ext else base


def _upload_tmp_root() -> Path:
    root = getattr(settings, "MEATZE_UPLOAD_TMP_DIR", "")
    if root:
        p = Path(root)
    else:
        p = Path(settings.MEDIA_ROOT) / "_chunk_uploads"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _upload_dir(upload_id: str) -> Path:
    return _upload_tmp_root() / upload_id


def _meta_path(upload_id: str) -> Path:
    return _upload_dir(upload_id) / "meta.json"


def _part_path(upload_id: str) -> Path:
    return _upload_dir(upload_id) / "upload.part"


def _read_json(request):
    try:
        body = request.body.decode("utf-8")
        return json.loads(body or "{}")
    except Exception:
        return {}


def _write_meta(upload_id: str, data: dict):
    d = _upload_dir(upload_id)
    d.mkdir(parents=True, exist_ok=True)
    _meta_path(upload_id).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _read_meta(upload_id: str) -> dict:
    p = _meta_path(upload_id)
    if not p.exists():
        raise FileNotFoundError("meta_not_found")
    return json.loads(p.read_text(encoding="utf-8"))


def _require_teacher(user, curso: Curso) -> bool:
    return Enrol.objects.filter(user=user, codigo=curso.codigo, role="teacher").exists()


def _infer_module_from_path_local(curso, target_path: str) -> str:
    tp = (target_path or "").strip().strip("/")
    if not tp:
        return ""

    parts = tp.split("/")
    prefixes = []
    cur = ""
    for p in parts:
        cur = f"{cur}/{p}" if cur else p
        prefixes.append(cur)

    locked = (
        CursoFolder.objects
        .filter(curso=curso, is_deleted=False, is_locked=True, path__in=prefixes)
        .values("path", "title")
    )

    if not locked:
        return ""

    best = sorted(locked, key=lambda x: len(x["path"] or ""), reverse=True)[0]
    title = (best.get("title") or "").strip()
    return title or best["path"].split("/")[-1]


def _tipo_from_audience(aud: str) -> str:
    aud = (aud or "").strip()
    if aud == "docentes":
        return CursoFile.TIPO_DOCENTES
    if aud == "mis":
        return CursoFile.TIPO_PRIVADO
    return CursoFile.TIPO_ALUMNOS

@csrf_exempt
@login_required
@require_profile_complete
@require_POST
def materiales_upload_init(request, codigo):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        raise Http404

    if not _require_teacher(request.user, curso):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    data = _read_json(request)

    filename = _safe_name(data.get("filename") or "file")
    filesize = int(data.get("filesize") or 0)
    folder_path = _normalize_path(data.get("folder_path") or "")
    audience = (data.get("audience") or "alumnos").strip()
    content_type = (data.get("content_type") or "application/octet-stream").strip()
    chunk_size = int(data.get("chunk_size") or 0)

    if filesize <= 0:
        return JsonResponse({"ok": False, "error": "bad_filesize"}, status=400)

    upload_id = uuid.uuid4().hex
    meta = {
        "upload_id": upload_id,
        "curso_codigo": curso.codigo,
        "user_id": request.user.id,
        "filename": filename,
        "filesize": filesize,
        "folder_path": folder_path,
        "audience": audience,
        "content_type": content_type,
        "chunk_size": chunk_size,
        "received_bytes": 0,
    }
    _write_meta(upload_id, meta)

    return JsonResponse({
        "ok": True,
        "upload_id": upload_id,
    })

@csrf_exempt
@login_required
@require_profile_complete
@require_POST
def materiales_upload_chunk(request, codigo):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        raise Http404

    if not _require_teacher(request.user, curso):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    upload_id = (request.POST.get("upload_id") or "").strip()
    chunk_index = int(request.POST.get("chunk_index") or 0)

    if not upload_id:
        return JsonResponse({"ok": False, "error": "no_upload_id"}, status=400)

    try:
        meta = _read_meta(upload_id)
    except FileNotFoundError:
        return JsonResponse({"ok": False, "error": "upload_not_found"}, status=404)

    if meta.get("curso_codigo") != curso.codigo or int(meta.get("user_id") or 0) != request.user.id:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    chunk = request.FILES.get("chunk")
    if not chunk:
        return JsonResponse({"ok": False, "error": "no_chunk"}, status=400)

    chunk_size = int(meta.get("chunk_size") or 0)
    offset = chunk_index * chunk_size if chunk_size > 0 else None

    part_file = _part_path(upload_id)
    part_file.parent.mkdir(parents=True, exist_ok=True)

    mode = "r+b" if part_file.exists() else "wb"
    with open(part_file, mode) as fh:
        if offset is not None:
            fh.seek(offset)
        for piece in chunk.chunks():
            fh.write(piece)

    meta["received_bytes"] = int(part_file.stat().st_size)
    _write_meta(upload_id, meta)

    return JsonResponse({
        "ok": True,
        "upload_id": upload_id,
        "received_bytes": meta["received_bytes"],
        "chunk_index": chunk_index,
    })


@csrf_exempt
@login_required
@require_profile_complete
@require_POST
def materiales_upload_complete(request, codigo):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        raise Http404

    if not _require_teacher(request.user, curso):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    data = _read_json(request)
    upload_id = (data.get("upload_id") or "").strip()
    if not upload_id:
        return JsonResponse({"ok": False, "error": "no_upload_id"}, status=400)

    try:
        meta = _read_meta(upload_id)
    except FileNotFoundError:
        return JsonResponse({"ok": False, "error": "upload_not_found"}, status=404)

    if meta.get("curso_codigo") != curso.codigo or int(meta.get("user_id") or 0) != request.user.id:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    part_file = _part_path(upload_id)
    if not part_file.exists():
        return JsonResponse({"ok": False, "error": "part_missing"}, status=400)

    real_size = int(part_file.stat().st_size)
    expected_size = int(meta.get("filesize") or 0)
    if expected_size <= 0 or real_size != expected_size:
        return JsonResponse({
            "ok": False,
            "error": "size_mismatch",
            "expected": expected_size,
            "received": real_size,
        }, status=400)

    filename = _safe_name(meta.get("filename") or "file")
    folder_path = _normalize_path(meta.get("folder_path") or "")
    audience = (meta.get("audience") or "alumnos").strip()
    tipo = _tipo_from_audience(audience)

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    module_key = _infer_module_from_path_local(curso, folder_path)

    with open(part_file, "rb") as fh:
        obj = CursoFile(
            curso=curso,
            uploaded_by=request.user,
            tipo=tipo,
            folder_path=folder_path,
            module_key=module_key,
            title=filename,
            size=real_size,
            ext=ext,
        )
        obj.file.save(filename, fh, save=True)

    file_html = render_to_string(
        "panel/partials/materiales_tree_file.html",
        {"f": obj, "is_teacher": True, "audience": audience},
        request=request,
    )

    shutil.rmtree(_upload_dir(upload_id), ignore_errors=True)

    return JsonResponse({
        "ok": True,
        "upload_id": upload_id,
        "files": [{
            "id": obj.id,
            "file_html": file_html,
        }],
    })

import requests
from django.core.files.base import File

GOOGLE_WORKSPACE_MIME_PREFIX = "application/vnd.google-apps."

GOOGLE_WORKSPACE_EXPORTS = {
    "application/vnd.google-apps.document": {
        "export_mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ext": "docx",
    },
    "application/vnd.google-apps.spreadsheet": {
        "export_mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ext": "xlsx",
    },
    "application/vnd.google-apps.presentation": {
        "export_mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "ext": "pptx",
    },
    "application/vnd.google-apps.drawing": {
        "export_mime": "application/pdf",
        "ext": "pdf",
    },
}


def _drive_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
    }


def _get_drive_file_meta(file_id: str, access_token: str) -> dict:
    url = (
        f"https://www.googleapis.com/drive/v3/files/{file_id}"
        f"?fields=id,name,mimeType,size"
    )

    with requests.get(url, headers=_drive_headers(access_token), timeout=(10, 60)) as r:
        if r.status_code == 401:
            raise ValueError("google_auth_failed")
        if r.status_code == 403:
            raise ValueError("google_forbidden")
        if r.status_code == 404:
            raise ValueError("google_file_not_found")
        r.raise_for_status()
        return r.json() or {}


def _replace_ext(filename: str, new_ext: str) -> str:
    filename = _safe_name(filename or "file")
    new_ext = (new_ext or "").strip().lstrip(".")
    if not new_ext:
        return filename

    if "." in filename:
        base = filename.rsplit(".", 1)[0]
    else:
        base = filename

    return _safe_name(f"{base}.{new_ext}")


def _download_drive_export(file_id: str, access_token: str, export_mime: str, out_path: Path):
    encoded_mime = quote(export_mime, safe="")
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType={encoded_mime}"

    with requests.get(url, headers=_drive_headers(access_token), stream=True, timeout=(10, 600)) as r:
        if r.status_code == 401:
            raise ValueError("google_auth_failed")
        if r.status_code == 403:
            raise ValueError("google_forbidden")
        if r.status_code == 404:
            raise ValueError("google_file_not_found")
        if r.status_code == 400:
            raise ValueError("google_export_not_supported")
        r.raise_for_status()

        with open(out_path, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
                    
def _download_drive_blob(file_id: str, access_token: str, out_path: Path):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    with requests.get(url, headers=_drive_headers(access_token), stream=True, timeout=(10, 600)) as r:
        if r.status_code == 401:
            raise ValueError("google_auth_failed")
        if r.status_code == 403:
            raise ValueError("google_forbidden")
        if r.status_code == 404:
            raise ValueError("google_file_not_found")
        r.raise_for_status()

        with open(out_path, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
                    
def _generated_storage_name(original_name: str) -> str:
    clean = _safe_name(original_name, max_base_len=40)
    if "." in clean:
        _, ext = clean.rsplit(".", 1)
        ext = "." + ext.lower()
    else:
        ext = ""
    return f"gdrv_{uuid.uuid4().hex[:12]}{ext}"

@csrf_exempt
@login_required
@require_profile_complete
@require_POST
def materiales_import_google_drive(request, codigo):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        raise Http404

    if not _require_teacher(request.user, curso):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    data = _read_json(request)

    file_id = (data.get("file_id") or "").strip()
    filename = _safe_name(data.get("name") or "drive_file")
    mime_type = (data.get("mime_type") or "").strip()
    folder_path = _normalize_path(data.get("folder_path") or "")
    audience = (data.get("audience") or "alumnos").strip()
    access_token = (data.get("access_token") or "").strip()

    if not file_id or not access_token:
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)

    tipo = _tipo_from_audience(audience)
    module_key = _infer_module_from_path_local(curso, folder_path)

    tmp_dir = _upload_tmp_root() / f"gdrive_{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        meta = _get_drive_file_meta(file_id, access_token)

        drive_name = _safe_name(meta.get("name") or filename or "drive_file")
        drive_mime = (meta.get("mimeType") or mime_type or "").strip()

        # Если фронт прислал странное имя/тип, доверяем метаданным Drive
        filename = drive_name
        mime_type = drive_mime

        if mime_type.startswith(GOOGLE_WORKSPACE_MIME_PREFIX):
            cfg = GOOGLE_WORKSPACE_EXPORTS.get(mime_type)
            if not cfg:
                return JsonResponse({
                    "ok": False,
                    "error": "google_workspace_type_not_supported"
                }, status=400)

            export_mime = cfg["export_mime"]
            export_ext = cfg["ext"]

            filename = _replace_ext(filename, export_ext)
            ext = export_ext

            tmp_file = tmp_dir / filename
            _download_drive_export(file_id, access_token, export_mime, tmp_file)

        else:
            # Обычный бинарный файл
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            tmp_file = tmp_dir / filename
            _download_drive_blob(file_id, access_token, tmp_file)

        real_size = int(tmp_file.stat().st_size)

        display_name = filename
        storage_name = _generated_storage_name(display_name)

        obj = CursoFile(
            curso=curso,
            uploaded_by=request.user,
            tipo=tipo,
            folder_path=folder_path,
            module_key=module_key,
            title=display_name,
            size=real_size,
            ext=ext,
        )
        obj.save()

        with open(tmp_file, "rb") as fh:
            obj.file.save(storage_name, File(fh), save=True)

        file_html = render_to_string(
            "panel/partials/materiales_tree_file.html",
            {"f": obj, "is_teacher": True, "audience": audience},
            request=request,
        )

        return JsonResponse({
            "ok": True,
            "files": [{
                "id": obj.id,
                "file_html": file_html,
            }],
        })

    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except requests.RequestException:
        return JsonResponse({"ok": False, "error": "google_download_failed"}, status=502)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        
def _list_drive_folder_children(folder_id: str, access_token: str) -> list[dict]:
    items = []
    page_token = None

    while True:
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken, files(id,name,mimeType,size)",
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token

        r = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=_drive_headers(access_token),
            params=params,
            timeout=(10, 60),
        )

        if r.status_code == 401:
            raise ValueError("google_auth_failed")
        if r.status_code == 403:
            raise ValueError("google_forbidden")
        r.raise_for_status()

        data = r.json() or {}
        items.extend(data.get("files") or [])
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return items
    

def parent_path(path: str) -> str:
    path = (path or "").strip("/")
    if not path:
        return ""
    parts = path.split("/")
    return "/".join(parts[:-1])

def leaf_name(path: str) -> str:
    path = (path or "").strip("/")
    if not path:
        return ""
    return path.split("/")[-1]
    
def _ensure_meatze_folder_path(curso, full_path: str, user, locked=False):
    full_path = normalize_path(full_path)
    if not full_path:
        return

    cur = ""
    for seg in full_path.split("/"):
        cur = f"{cur}/{seg}" if cur else seg

        create_folder(
            curso,
            parent_path=parent_path(cur),
            name=leaf_name(cur),
            user=user,
            locked=locked,
        )
        
def _import_drive_file_to_meatze(
    *,
    curso,
    user,
    drive_file_id: str,
    drive_name: str,
    drive_mime: str,
    folder_path: str,
    audience: str,
    access_token: str,
):
    tipo = _tipo_from_audience(audience)
    module_key = _infer_module_from_path_local(curso, folder_path)

    tmp_dir = _upload_tmp_root() / f"gdrive_{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        filename = _safe_name(drive_name or "drive_file")

        if drive_mime.startswith(GOOGLE_WORKSPACE_MIME_PREFIX):
            cfg = GOOGLE_WORKSPACE_EXPORTS.get(drive_mime)
            if not cfg:
                raise ValueError("google_workspace_type_not_supported")

            filename = _replace_ext(filename, cfg["ext"])
            ext = cfg["ext"]
            tmp_file = tmp_dir / filename
            _download_drive_export(drive_file_id, access_token, cfg["export_mime"], tmp_file)
        else:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            tmp_file = tmp_dir / filename
            _download_drive_blob(drive_file_id, access_token, tmp_file)

        real_size = int(tmp_file.stat().st_size)
        display_name = filename
        storage_name = _generated_storage_name(display_name)

        obj = CursoFile(
            curso=curso,
            uploaded_by=user,
            tipo=tipo,
            folder_path=folder_path,
            module_key=module_key,
            title=display_name,
            size=real_size,
            ext=ext,
        )
        obj.save()

        with open(tmp_file, "rb") as fh:
            obj.file.save(storage_name, File(fh), save=True)

        return obj

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        
def _import_drive_folder_recursive(
    *,
    curso,
    user,
    drive_folder_id: str,
    drive_folder_name: str,
    meatze_parent_path: str,
    audience: str,
    access_token: str,
    stats: dict,
):
    folder_name = _safe_name(drive_folder_name or "Carpeta")
    current_meatze_path = _normalize_path(
        f"{meatze_parent_path}/{folder_name}" if meatze_parent_path else folder_name
    )

    _ensure_meatze_folder_path(curso, current_meatze_path, user, locked=False)
    stats["folders_created"] += 1

    children = _list_drive_folder_children(drive_folder_id, access_token)

    for item in children:
        item_id = (item.get("id") or "").strip()
        item_name = item.get("name") or "file"
        item_mime = (item.get("mimeType") or "").strip()

        if not item_id:
            continue

        if item_mime == GOOGLE_DRIVE_FOLDER_MIME:
            _import_drive_folder_recursive(
                curso=curso,
                user=user,
                drive_folder_id=item_id,
                drive_folder_name=item_name,
                meatze_parent_path=current_meatze_path,
                audience=audience,
                access_token=access_token,
                stats=stats,
            )
        else:
            _import_drive_file_to_meatze(
                curso=curso,
                user=user,
                drive_file_id=item_id,
                drive_name=item_name,
                drive_mime=item_mime,
                folder_path=current_meatze_path,
                audience=audience,
                access_token=access_token,
            )
            stats["files_created"] += 1
            
@csrf_exempt
@login_required
@require_profile_complete
@require_POST
def materiales_import_google_drive_folder(request, codigo):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        raise Http404

    if not _require_teacher(request.user, curso):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    data = _read_json(request)

    folder_id = (data.get("folder_id") or "").strip()
    folder_name = (data.get("name") or "Carpeta").strip()
    target_path = _normalize_path(data.get("folder_path") or "")
    audience = (data.get("audience") or "alumnos").strip()
    access_token = (data.get("access_token") or "").strip()

    if not folder_id or not access_token:
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)

    stats = {
        "folders_created": 0,
        "files_created": 0,
    }

    try:
        _import_drive_folder_recursive(
            curso=curso,
            user=request.user,
            drive_folder_id=folder_id,
            drive_folder_name=folder_name,
            meatze_parent_path=target_path,
            audience=audience,
            access_token=access_token,
            stats=stats,
        )

        return JsonResponse({
            "ok": True,
            "folders_created": stats["folders_created"],
            "files_created": stats["files_created"],
        })

    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except requests.RequestException:
        return JsonResponse({"ok": False, "error": "google_download_failed"}, status=502)
        
        
@csrf_exempt
@login_required
@require_profile_complete
@require_POST
def materiales_drive_list_folder(request, codigo):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        raise Http404

    if not _require_teacher(request.user, curso):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    data = _read_json(request)

    folder_id = (data.get("folder_id") or "").strip()
    access_token = (data.get("access_token") or "").strip()

    if not folder_id or not access_token:
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)

    try:
        items = _list_drive_folder_children(folder_id, access_token)
        return JsonResponse({
            "ok": True,
            "items": [
                {
                    "id": (x.get("id") or "").strip(),
                    "name": x.get("name") or "",
                    "mimeType": (x.get("mimeType") or "").strip(),
                    "size": int(x.get("size") or 0),
                    "is_folder": (x.get("mimeType") == GOOGLE_DRIVE_FOLDER_MIME),
                }
                for x in items if (x.get("id") or "").strip()
            ]
        })
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except requests.RequestException:
        return JsonResponse({"ok": False, "error": "google_list_failed"}, status=502)
        
@csrf_exempt
@login_required
@require_profile_complete
@require_POST
def materiales_drive_create_folder(request, codigo):
    curso = Curso.objects.filter(codigo=codigo).first()
    if not curso:
        raise Http404

    if not _require_teacher(request.user, curso):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    data = _read_json(request)

    parent_path = _normalize_path(data.get("parent_path") or "")
    folder_name = (data.get("name") or "").strip()

    if not folder_name:
        return JsonResponse({"ok": False, "error": "empty_name"}, status=400)

    try:
        folder, created = create_folder(
            curso,
            parent_path=parent_path,
            name=folder_name,
            user=request.user,
            locked=False,
        )
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

    return JsonResponse({
        "ok": True,
        "created": bool(created),
        "path": folder.path,
        "title": folder.title or leaf_name(folder.path),
    })