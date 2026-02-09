# panel/materiales_fs.py
import re
from django.db import IntegrityError, transaction
from .models import CursoFolder

def normalize_path(p: str) -> str:
    p = (p or "").strip().replace("\\", "/").strip("/")
    p = re.sub(r"/{2,}", "/", p)
    return p

def join_path(parent: str, name: str) -> str:
    parent = normalize_path(parent)
    name = normalize_path(name)
    if not name:
        return ""
    return normalize_path(f"{parent}/{name}" if parent else name)

def create_folder(curso, *, parent_path: str, name: str, user, locked=False):
    """
    Создаёт папку внутри parent_path.
    Возвращает (obj, created).
    """
    base = normalize_path(name)
    if not base:
        raise ValueError("empty_name")

    full = join_path(parent_path, base)

    # (опционально) запретить создание под "locked" родителем:
    # если хочешь — включи:
    # if parent_path:
    #     par = CursoFolder.objects.filter(curso=curso, path=normalize_path(parent_path), is_deleted=False).first()
    #     if par and par.is_locked:
    #         raise ValueError("parent_locked")

    try:
        with transaction.atomic():
            obj, created = CursoFolder.objects.get_or_create(
                curso=curso,
                path=full,
                defaults={"title": base, "created_by": user, "is_locked": bool(locked)}
            )
            if not created and obj.is_deleted:
                obj.is_deleted = False
                obj.save(update_fields=["is_deleted"])
        return obj, created
    except IntegrityError:
        # race condition / unique_together
        obj = CursoFolder.objects.filter(curso=curso, path=full).first()
        return obj, False