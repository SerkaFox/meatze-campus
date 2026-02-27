from api.utils_temp import (
    ensure_teacher_of_course,
    is_teacher, two_digit_code,
    local_from_name, domain_from_course,
)
from api.models import Curso, Enrol, UserProfile
from api.utils_temp import CsrfExemptSessionAuthentication
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth.backends import ModelBackend
from django.views.decorators.csrf import csrf_exempt
from panel.models import Curso, TempAccess
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, AllowAny, IsAuthenticated
from rest_framework.response import Response

def build_me(user):
    return {
        "id": user.id,
        "email": user.email or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "is_teacher": bool(getattr(user, "is_staff", False)),
        "has_password": bool(user.has_usable_password()),
    }
    
User = get_user_model()
def split_full_name(full_name: str):
    parts = [p for p in (full_name or "").strip().split() if p]
    if not parts:
        return "", "", ""
    first = parts[0]
    # всё остальное — апеллидо
    rest = parts[1:]
    last1 = rest[0] if len(rest) >= 1 else ""
    last2 = " ".join(rest[1:]) if len(rest) >= 2 else ""
    return first, last1, last2


# --- POST /meatze/v5/teacher/temp/create ----------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def teacher_temp_create(request):
    user = request.user
    if not is_teacher(user):
        return Response({"message": "Docente requerido"}, status=403)

    course_code = (request.data.get("course_code") or "").strip()
    count = int(request.data.get("count") or 0)
    mode = (request.data.get("mode") or "set").lower()

    try:
        curso = Curso.objects.get(codigo=course_code)
    except Curso.DoesNotExist:
        return Response({"message": "Curso no encontrado"}, status=404)

    if not ensure_teacher_of_course(user, curso):
        return Response({"message": "No eres docente de este curso"}, status=403)

    count = max(0, min(99, count))

    qs = TempAccess.objects.filter(teacher=user, curso=curso)

    # Упрощённо: поддерживаем только mode="set" (как в JS).
    if count == 0:
        qs.delete()
        return Response({"ok": True, "items": []})

    # существующие по имени -> obj
    existing_by_name = {ta.temp_name: ta for ta in qs}
    # сначала убираем всё, что выходит за пределы count
    for ta in list(existing_by_name.values()):
        if ta.temp_name.startswith("Alumno"):
            try:
                ix = int(ta.temp_name.replace("Alumno", ""))
            except ValueError:
                ix = None
            if ix is not None and ix > count:
                ta.delete()
                existing_by_name.pop(ta.temp_name, None)

    # создаём/оставляем Alumno01..AlumnoNN
    for ix in range(1, count + 1):
        name = f"Alumno{ix:02d}"
        ta = existing_by_name.get(name)

        if ta is None:
            TempAccess.objects.create(
                teacher=user,
                curso=curso,
                temp_name=name,
                key=two_digit_code(),
                used=False,
            )
        else:
            # ✅ ВАЖНО: если уже использован — реюзаем слот
            if ta.used:
                ta.key = two_digit_code()
                ta.used = False
                ta.save(update_fields=["key", "used", "updated_at"])

    # перечитываем заново
    items = TempAccess.objects.filter(
        teacher=user, curso=curso
    ).order_by("temp_name")

    return Response({
        "ok": True,
        "items": [
            {"temp_name": t.temp_name, "key": t.key}
            for t in items
        ],
    })
    

# --- GET /meatze/v5/teacher/temp/list -------------------------------
@csrf_exempt
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def teacher_temp_list(request):
    user = request.user
    if not is_teacher(user):
        return Response({"message": "Docente requerido"}, status=403)

    course_code = (request.query_params.get("course_code") or "").strip()
    try:
        curso = Curso.objects.get(codigo=course_code)
    except Curso.DoesNotExist:
        return Response({"message": "Curso no encontrado"}, status=404)

    if not ensure_teacher_of_course(user, curso):
        return Response({"message": "No eres docente de este curso"}, status=403)

    items = TempAccess.objects.filter(
        teacher=user, curso=curso, used=False
    ).order_by("temp_name")

    return Response({
        "ok": True,
        "items": [
            {"temp_name": t.temp_name, "key": t.key}
            for t in items
        ],
    })


# --- POST /meatze/v5/teacher/temp/rotate ----------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def teacher_temp_rotate(request):
    user = request.user
    if not is_teacher(user):
        return Response({"message": "Docente requerido"}, status=403)

    course_code = (request.data.get("course_code") or "").strip()
    temp_name = (request.data.get("temp_name") or "").strip()

    try:
        curso = Curso.objects.get(codigo=course_code)
    except Curso.DoesNotExist:
        return Response({"message": "Curso no encontrado"}, status=404)

    if not ensure_teacher_of_course(user, curso):
        return Response({"message": "No eres docente de este curso"}, status=403)

    try:
        ta = TempAccess.objects.get(
            teacher=user, curso=curso, temp_name=temp_name
        )
    except TempAccess.DoesNotExist:
        return Response({"message": "No encontrado"}, status=404)

    ta.key = two_digit_code()
    ta.used = False
    ta.save(update_fields=["key", "used", "updated_at"])

    return Response({"ok": True, "key": ta.key})

# --- GET /meatze/v5/auth/temp_accounts ------------------------------
@csrf_exempt
@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def auth_temp_accounts(request):
    course_code = (request.query_params.get("course_code") or "").strip()
    try:
        curso = Curso.objects.get(codigo=course_code)
    except Curso.DoesNotExist:
        return Response({"message": "Curso no encontrado"}, status=404)

    # все преподы этого курса
    teacher_ids = Enrol.objects.filter(
        codigo=curso.codigo, role="teacher"
    ).values_list("user_id", flat=True)

    items_qs = TempAccess.objects.filter(
        curso=curso, teacher_id__in=teacher_ids, used=False
    ).values_list("temp_name", flat=True).distinct().order_by("temp_name")

    return Response({"items": list(items_qs)})


# --- POST /meatze/v5/auth/temp_verify -------------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def auth_temp_verify(request):
    course_code = (request.data.get("course_code") or "").strip()
    temp_name = (request.data.get("temp_name") or "").strip()
    key = (request.data.get("key") or "").strip()

    if len(key) == 1:
        key = "0" + key

    try:
        curso = Curso.objects.get(codigo=course_code)
    except Curso.DoesNotExist:
        return Response({"message": "Curso no encontrado"}, status=404)

    teacher_ids = Enrol.objects.filter(
        codigo=curso.codigo, role="teacher"
    ).values_list("user_id", flat=True)

    ok = TempAccess.objects.filter(
        curso=curso,
        teacher_id__in=teacher_ids,
        temp_name=temp_name,
        key=key,
        used=False,
    ).exists()

    if not ok:
        return Response({"message": "Invalid code"}, status=403)

    return Response({"ok": True})
    

# --- POST /meatze/v5/auth/temp_claim --------------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def auth_temp_claim(request):
    course_code = (request.data.get("course_code") or "").strip()
    temp_name = (request.data.get("temp_name") or "").strip()
    key = (request.data.get("key") or "").strip()
    full_name = (request.data.get("full_name") or "").strip()
    password = (request.data.get("password") or "")

    if len(key) == 1:
        key = "0" + key

    if not (course_code and temp_name and key and full_name and len(password) >= 6):
        return Response(
            {"message": "course_code/temp_name/key/full_name/password"},
            status=400,
        )

    try:
        curso = Curso.objects.get(codigo=course_code)
    except Curso.DoesNotExist:
        return Response({"message": "Curso no encontrado"}, status=404)

    teacher_ids = Enrol.objects.filter(
        codigo=curso.codigo, role="teacher"
    ).values_list("user_id", flat=True)

    tas = list(TempAccess.objects.filter(
        curso=curso,
        teacher_id__in=teacher_ids,
        temp_name=temp_name,
        key=key,
        used=False,
    ))

    if not tas:
        return Response({"message": "Invalid code"}, status=403)

    # помечаем как использованный у всех учителей
    for ta in tas:
        ta.used = True
        ta.save(update_fields=["used", "updated_at"])

    # создаём пользователя
    local = local_from_name(full_name)
    domain = domain_from_course(course_code)
    base_email = f"{local}@{domain}.es"
    email = base_email
    i = 0
    while User.objects.filter(email=email).exists():
        i += 1
        email = f"{local}+{i}@{domain}.es"

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
    )
    # можно ещё раскидать first_name/last_name, но не обязательно
    first, last1, last2 = split_full_name(full_name)
    
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.first_name = first
    profile.last_name1 = last1
    profile.last_name2 = last2
    profile.display_name = full_name
    profile.save(update_fields=["first_name","last_name1","last_name2","display_name"])
    # энроллим в курс
    Enrol.objects.get_or_create(
        user=user,
        codigo=curso.codigo,
        defaults={"role": "student"},
    )

    django_request = getattr(request, "_request", request)

    # важно: указать backend (иначе иногда "backend isn't set")
    user.backend = "django.contrib.auth.backends.ModelBackend"
    django_login(django_request, user)

    return Response({"ok": True, "email": email, "me": build_me(user)})
# POST /meatze/v5/teacher/alumno/reset_pass
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
def teacher_alumno_reset_pass(request):
    user = request.user
    if not is_teacher(user):
        return Response({"message": "Docente requerido"}, status=403)

    course_code = (request.data.get("course_code") or "").strip()
    student_id = int(request.data.get("user_id") or 0)

    if not (course_code and student_id > 0):
        return Response({"message": "course_code/user_id"}, status=400)

    try:
        curso = Curso.objects.get(codigo=course_code)
    except Curso.DoesNotExist:
        return Response({"message": "Curso no encontrado"}, status=404)

    if not ensure_teacher_of_course(user, curso):
        return Response({"message": "No eres docente de este curso"}, status=403)

    # проверяем, что user_id действительно студент этого курса
    ok_student = Enrol.objects.filter(
        codigo=curso.codigo,
        user_id=student_id,
    ).exclude(role="teacher").exists()

    if not ok_student:
        return Response(
            {"message": "Alumno no está en este curso"},
            status=404,
        )

    # 4-значный PIN
    new_pin = f"{random.randint(0, 9999):04d}"

    try:
        alumno = User.objects.get(pk=student_id)
    except User.DoesNotExist:
        return Response({"message": "Alumno no encontrado"}, status=404)

    alumno.set_password(new_pin)
    alumno.save(update_fields=["password"])

    return Response({"ok": True, "password": new_pin})

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from django.contrib.auth import get_user_model
from .models import PendingRole, UserProfile, Enrol
from .views import require_admin_token  # если он у тебя в api/views.py — импортируй корректно

User = get_user_model()

@require_admin_token
@require_http_methods(["GET"])
def admin_pending_list(request):
    qs = (
        PendingRole.objects
        .filter(status="pending")
        .select_related("user")
        .order_by("-created_at")
    )

    items = []
    for p in qs:
        u = p.user
        prof = getattr(u, "profile", None)
        items.append({
            "id": p.id,
            "user_id": u.id,
            "email": p.email,
            "display_name": (getattr(prof, "display_name", "") or u.get_full_name() or u.email or u.username),
            "requested_role": p.requested_role,
            "created_at": p.created_at.isoformat(),
            "is_staff": bool(getattr(u, "is_staff", False)),
        })

    return JsonResponse({"items": items})

@csrf_exempt
@require_admin_token
@require_http_methods(["POST"])
def admin_pending_approve_teacher(request, pending_id: int):
    try:
        p = PendingRole.objects.select_related("user").get(pk=pending_id, status="pending")
    except PendingRole.DoesNotExist:
        return JsonResponse({"ok": False, "message": "not_found"}, status=404)

    u = p.user

    # делаем docente
    u.is_staff = True
    u.save(update_fields=["is_staff"])

    profile, _ = UserProfile.objects.get_or_create(user=u)
    profile.is_teacher = True
    profile.save(update_fields=["is_teacher"])

    # закрываем pending
    p.status = "approved"
    p.decided_role = "teacher"
    p.decided_at = timezone.now()
    p.save(update_fields=["status", "decided_role", "decided_at"])

    return JsonResponse({"ok": True})


@csrf_exempt
@require_admin_token
@require_http_methods(["POST"])
def admin_pending_mark_student(request, pending_id: int):
    try:
        p = PendingRole.objects.select_related("user").get(pk=pending_id, status="pending")
    except PendingRole.DoesNotExist:
        return JsonResponse({"ok": False, "message": "not_found"}, status=404)

    u = p.user

    # гарантируем что НЕ docente
    u.is_staff = False
    u.save(update_fields=["is_staff"])

    profile, _ = UserProfile.objects.get_or_create(user=u)
    profile.is_teacher = False
    profile.save(update_fields=["is_teacher"])

    # чистим teacher enrols на всякий случай
    Enrol.objects.filter(user=u, role="teacher").delete()

    # по твоему требованию: если это alumno — из списка удаляется
    p.delete()

    return JsonResponse({"ok": True})
