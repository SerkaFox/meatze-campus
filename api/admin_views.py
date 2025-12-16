# api/admin_views.py
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Curso, Enrol

User = get_user_model()


def _check_admin(request):
    """
    Общая проверка токена ?adm=... или X-MZ-Admin.
    Совпадает с твоим admin_ping.
    """
    token = request.GET.get("adm") or request.headers.get("X-MZ-Admin")
    expected = getattr(settings, "MEATZE_ADMIN_PASS", "MeatzeIT")
    if token != expected:
        return Response({"ok": False, "error": "forbidden"}, status=403)
    return None


# ========== DOCENTES ==========

@api_view(["GET", "POST"])
def admin_teachers(request):
    """
    GET  /meatze/v5/admin/teachers
    POST /meatze/v5/admin/teachers   (upsert по email)
    """
    err = _check_admin(request)
    if err:
        return err

    if request.method == "GET":
        teachers = User.objects.filter(is_teacher=True).order_by("first_name", "last_name")
        items = []
        for u in teachers:
            # делим last_name на 2 части (как в WP)
            ln1 = ""
            ln2 = ""
            if u.last_name:
                parts = u.last_name.split()
                if parts:
                    ln1 = parts[0]
                    ln2 = " ".join(parts[1:])
            items.append({
                "id": u.id,
                "email": u.email,
                "first_name": u.first_name or "",
                "last_name1": ln1,
                "last_name2": ln2,
                "display_name": u.get_full_name() or u.email,
                "bio": getattr(u, "bio", "") or "",
            })
        return Response({"items": items})

    # POST: создать/обновить по email
    data = request.data or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return Response({"error": "email_required"}, status=400)

    first = (data.get("first_name") or "").strip()
    ln1 = (data.get("last_name1") or "").strip()
    ln2 = (data.get("last_name2") or "").strip()
    bio = (data.get("bio") or "").strip()

    last_name = " ".join(p for p in [ln1, ln2] if p).strip()

    user, _created = User.objects.get_or_create(email=email, defaults={
        "username": email,
    })
    # обновляем поля
    if first:
        user.first_name = first
    if last_name:
        user.last_name = last_name
    user.is_teacher = True
    if hasattr(user, "bio"):
        user.bio = bio
    user.save()

    return Response({"ok": True, "id": user.id})
    

@api_view(["POST"])
def admin_teacher_update(request, pk: int):
    """
    POST /meatze/v5/admin/teachers/<id>
    """
    err = _check_admin(request)
    if err:
        return err

    try:
        user = User.objects.get(pk=pk, is_teacher=True)
    except User.DoesNotExist:
        return Response({"error": "not_found"}, status=404)

    data = request.data or {}
    email = (data.get("email") or "").strip().lower()
    first = (data.get("first_name") or "").strip()
    ln1 = (data.get("last_name1") or "").strip()
    ln2 = (data.get("last_name2") or "").strip()
    bio = (data.get("bio") or "").strip()

    last_name = " ".join(p for p in [ln1, ln2] if p).strip()

    if email:
        user.email = email
        # если юзер создавался по email как username
        if user.username == "" or "@" in user.username:
            user.username = email
    user.first_name = first
    user.last_name = last_name
    if hasattr(user, "bio"):
        user.bio = bio
    user.is_teacher = True
    user.save()

    return Response({"ok": True})


@api_view(["POST"])
def admin_teacher_delete(request, pk: int):
    """
    POST /meatze/v5/admin/teachers/<id>/delete
    Важно: лучше НЕ удалять юзера, а просто снять флаг is_teacher.
    """
    err = _check_admin(request)
    if err:
        return err

    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({"error": "not_found"}, status=404)

    user.is_teacher = False
    user.save()
    return Response({"ok": True})
# ========== CURSOS (ADMIN) ==========

def _curso_to_item(c: Curso):
    return {
        "id": c.id,
        "codigo": c.codigo,
        "titulo": c.titulo,
        "horas": c.horas_total,
        "modules": c.modules or [],
    }


@api_view(["GET"])
def admin_cursos_list(request):
    """
    GET /meatze/v5/admin/cursos
    """
    err = _check_admin(request)
    if err:
        return err

    cursos = Curso.objects.all().order_by("codigo")
    items = [_curso_to_item(c) for c in cursos]
    return Response({"items": items})


@api_view(["POST"])
def admin_cursos_upsert(request):
    """
    POST /meatze/v5/admin/cursos/upsert

    Body: { codigo, titulo, modules: [ {name, hours}, ... ], id? }
    """
    err = _check_admin(request)
    if err:
        return err

    data = request.data or {}
    codigo = (data.get("codigo") or "").strip()
    titulo = (data.get("titulo") or "").strip()
    modules = data.get("modules") or []

    if not codigo or not titulo:
        return Response({"error": "codigo_y_titulo_requeridos"}, status=400)

    # считаем часы
    total_horas = 0
    norm_modules = []
    for m in modules:
        name = (m.get("name") or "").strip()
        hours = int(m.get("hours") or 0)
        if not name:
            continue
        if hours < 0:
            hours = 0
        total_horas += hours
        norm_modules.append({"name": name, "hours": hours})

    cid = data.get("id")
    if cid:
        try:
            curso = Curso.objects.get(pk=cid)
        except Curso.DoesNotExist:
            curso = Curso.objects.filter(codigo=codigo).first()
    else:
        curso = Curso.objects.filter(codigo=codigo).first()

    if not curso:
        curso = Curso(codigo=codigo)

    curso.titulo = titulo
    curso.modules = norm_modules
    curso.horas_total = total_horas
    curso.save()

    return Response({"ok": True, "id": curso.id})


@api_view(["POST"])
def admin_curso_delete(request, pk: int):
    """
    POST /meatze/v5/admin/cursos/<id>/delete
    """
    err = _check_admin(request)
    if err:
        return err

    try:
        curso = Curso.objects.get(pk=pk)
    except Curso.DoesNotExist:
        return Response({"error": "not_found"}, status=404)

    curso.delete()
    return Response({"ok": True})

@api_view(["GET"])
def admin_enrolments(request):
    """
    GET /meatze/v5/admin/enrolments?codigo=IFCT0209&role=teacher
    """
    err = _check_admin(request)
    if err:
        return err

    codigo = request.GET.get("codigo") or ""
    role = request.GET.get("role") or "teacher"

    qs = Enrol.objects.select_related("user")
    if codigo:
        qs = qs.filter(codigo=codigo)
    if role:
        qs = qs.filter(role=role)

    items = []
    for e in qs:
        u = e.user
        items.append({
            "id": e.id,
            "user_id": u.id,
            "uid": u.id,
            "uid_str": str(u.id),
            "email": u.email,
            "display_name": u.get_full_name() or u.email,
            "role": e.role,
            "codigo": e.codigo,
        })
    return Response({"items": items})


@api_view(["POST"])
def admin_cursos_assign(request):
    """
    POST /meatze/v5/admin/cursos/assign
    Body: { curso_codigo: "IFCT0209", teachers: ["12","34",...] }
    """
    err = _check_admin(request)
    if err:
        return err

    data = request.data or {}
    codigo = (data.get("curso_codigo") or "").strip()
    teachers_ids = data.get("teachers") or []

    if not codigo:
        return Response({"error": "curso_codigo_requerido"}, status=400)

    # нормализуем ID
    teacher_ids_int = []
    for t in teachers_ids:
        try:
            teacher_ids_int.append(int(t))
        except (TypeError, ValueError):
            continue

    # существующие назначения
    existing = Enrol.objects.filter(codigo=codigo, role="teacher")
    existing_by_user = {e.user_id: e for e in existing}

    # DELETE тех, кого теперь нет в списке
    for uid, enrol in list(existing_by_user.items()):
        if uid not in teacher_ids_int:
            enrol.delete()

    # ADD тех, кого нет
    for uid in teacher_ids_int:
        if uid in existing_by_user:
            continue
        try:
            user = User.objects.get(pk=uid)
        except User.DoesNotExist:
            continue
        Enrol.objects.get_or_create(
            user=user,
            codigo=codigo,
            role="teacher",
        )

    return Response({"ok": True, "assigned": len(teacher_ids_int)})
