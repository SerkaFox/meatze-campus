import json
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile


def _get_or_create_profile(user: User) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile
    
@csrf_exempt
@login_required
def me_change_password(request):
    """
    POST /meatze/v5/me/password
    { "password": "...." }

    Меняет пароль текущему залогиненному пользователю.
    """
    if request.method != "POST":
        return JsonResponse({"message": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"message": "JSON inválido"}, status=400)

    password = (data.get("password") or "").strip()
    if len(password) < 6:
        return JsonResponse(
            {"message": "Contraseña demasiado corta (mín. 6)."},
            status=400,
        )

    user = request.user
    user.set_password(password)
    user.save()

    # чтобы сессия не отвалилась после смены пароля
    update_session_auth_hash(request, user)

    return JsonResponse(
        {"ok": True, "message": "Contraseña actualizada."}
    )

def _build_profile_dict(user, profile):
    """
    Формат под фронт:
    pr = p.profile || p;
    fFirst.value = pr.first_name;
    fLast1.value = pr.last_name1;
    ...
    """
    first_name = (
        (profile.first_name if profile and profile.first_name else user.first_name)
        or ""
    ).strip()

    last1 = (profile.last_name1 if profile else "") or ""
    last2 = (profile.last_name2 if profile else "") or ""
    display_name = (
        profile.display_name
        if profile and profile.display_name
        else (user.get_full_name() or user.username or user.email)
    ) or ""
    bio = (profile.bio if profile else "") or ""

    return {
        "id": user.id,
        "email": user.email or user.username,
        "first_name": first_name,
        "last_name1": last1,
        "last_name2": last2,
        "display_name": display_name,
        "bio": bio,
    }

# api/profile_views.py
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .models import UserProfile, Enrol, Curso

def _get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile

def _is_teacher(user, profile=None):
    # у тебя teacher = staff
    if getattr(user, "is_staff", False):
        return True
    if profile and getattr(profile, "is_teacher", False):
        return True
    return False

def _norm_codigos(arr):
    out = []
    for x in (arr or []):
        s = (str(x) or "").strip().upper()
        if s:
            out.append(s)
    # уникализируем, сохраняя порядок
    seen = set()
    uniq = []
    for c in out:
        if c in seen:
            continue
        seen.add(c)
        uniq.append(c)
    return uniq

def _teacher_courses_payload(user):
    codigos = list(
        Enrol.objects.filter(user=user, role="teacher")
        .values_list("codigo", flat=True)
    )
    codigos = [c.strip().upper() for c in codigos if (c or "").strip()]

    titulo_by_codigo = dict(
        Curso.objects.filter(codigo__in=codigos).values_list("codigo", "titulo")
    )

    items = [{"codigo": c, "titulo": (titulo_by_codigo.get(c) or "")} for c in sorted(set(codigos))]
    return items
# api/profile_views.py
@csrf_exempt
@login_required
def me_profile(request):
    if request.method == "GET":
        profile = _get_or_create_profile(request.user)

        # нормальный display_name: явный -> сгенеренный -> email/username
        disp = (profile.display_name or "").strip()
        if not disp:
            disp = profile.build_display_name() or (request.user.get_full_name() or request.user.username or request.user.email or "")

        data = {
            "first_name": profile.first_name or "",
            "last_name1": profile.last_name1 or "",
            "last_name2": profile.last_name2 or "",
            "display_name": disp,
            "bio": profile.bio or "",
            "is_teacher": _is_teacher(request.user, profile),
            "teacher_courses": _teacher_courses_payload(request.user) if _is_teacher(request.user, profile) else [],
        }
        return JsonResponse({"profile": data})

    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            return JsonResponse({"message": "JSON inválido"}, status=400)

        profile = _get_or_create_profile(request.user)

        # ✅ PATCH semantics: меняем только если ключ реально есть
        if "first_name" in data:
            profile.first_name = (data.get("first_name") or "").strip()
        if "last_name1" in data:
            profile.last_name1 = (data.get("last_name1") or "").strip()
        if "last_name2" in data:
            profile.last_name2 = (data.get("last_name2") or "").strip()
        if "bio" in data:
            profile.bio = (data.get("bio") or "").strip()

        # display_name:
        # - если ключа нет -> не трогаем (важно для teacher_add/remove)
        # - если ключ есть:
        #     - не пустой -> сохраняем как есть
        #     - пустой -> автогенерим из FIO
        if "display_name" in data:
            incoming = (data.get("display_name") or "").strip()
            profile.display_name = incoming or (profile.build_display_name() or "")

        # важно: save() у тебя сам генерит display_name если пусто и FIO есть
        profile.save()

        # ✅ синхронизация в User — тоже только если реально меняли поля (иначе опять можно затереть)
        upd_user = []
        if "first_name" in data:
            request.user.first_name = profile.first_name
            upd_user.append("first_name")
        if "last_name1" in data:
            request.user.last_name = profile.last_name1
            upd_user.append("last_name")
        if upd_user:
            request.user.save(update_fields=upd_user)

        # --- teacher_add/remove как у тебя было ---
        if _is_teacher(request.user, profile):
            add_codes = _norm_codigos(data.get("teacher_add"))
            rem_codes = _norm_codigos(data.get("teacher_remove"))

            valid_codes = set(
                Curso.objects.filter(codigo__in=(add_codes + rem_codes)).values_list("codigo", flat=True)
            )
            add_codes = [c for c in add_codes if c in valid_codes]
            rem_codes = [c for c in rem_codes if c in valid_codes]

            from django.db import transaction
            with transaction.atomic():
                if rem_codes:
                    Enrol.objects.filter(user=request.user, role="teacher", codigo__in=rem_codes).delete()
                if add_codes:
                    existing = set(
                        Enrol.objects.filter(user=request.user, role="teacher", codigo__in=add_codes)
                        .values_list("codigo", flat=True)
                    )
                    for c in add_codes:
                        if c not in existing:
                            Enrol.objects.create(user=request.user, role="teacher", codigo=c)

        # payload: тоже с нормальным display_name
        disp = (profile.display_name or "").strip() or (profile.build_display_name() or "")
        payload = {
            "first_name": profile.first_name or "",
            "last_name1": profile.last_name1 or "",
            "last_name2": profile.last_name2 or "",
            "display_name": disp,
            "bio": profile.bio or "",
            "is_teacher": _is_teacher(request.user, profile),
            "teacher_courses": _teacher_courses_payload(request.user) if _is_teacher(request.user, profile) else [],
        }
        return JsonResponse({"message": "Datos guardados.", "profile": payload})

    return JsonResponse({"message": "Método no permitido"}, status=405)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_display(request):
    """
    GET /meatze/v5/user_display?email=...
    Возвращает красивое имя для e-mail.
    """
    email = (request.query_params.get("email") or "").strip().lower()
    if not email:
        return Response({"display_name": ""})

    u = User.objects.filter(email__iexact=email).first()
    if not u:
        return Response({"display_name": ""})

    name = u.get_full_name() or u.first_name or u.email
    return Response({"display_name": name})
    

def _auto_display_name(first_name: str, last1: str, last2: str, fallback: str = "") -> str:
    parts = [ (first_name or "").strip(), (last1 or "").strip(), (last2 or "").strip() ]
    s = " ".join([p for p in parts if p]).strip()
    return s or (fallback or "").strip()