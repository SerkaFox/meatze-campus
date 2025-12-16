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

@csrf_exempt
@login_required
def me_profile(request):
    """
    GET  /meatze/v5/me/profile  -> вернуть профиль
    POST /meatze/v5/me/profile  -> сохранить профиль
    """
    if request.method == "GET":
        profile = _get_or_create_profile(request.user)
        data = {
            "first_name": profile.first_name,
            "last_name1": profile.last_name1,
            "last_name2": profile.last_name2,
            "display_name": profile.display_name or "",
            "bio": profile.bio or "",
        }
        return JsonResponse({"profile": data})

    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"message": "JSON inválido"}, status=400)

        profile = _get_or_create_profile(request.user)

        profile.first_name = (data.get("first_name") or "").strip()
        profile.last_name1 = (data.get("last_name1") or "").strip()
        profile.last_name2 = (data.get("last_name2") or "").strip()
        profile.display_name = (data.get("display_name") or "").strip()
        profile.bio = (data.get("bio") or "").strip()
        profile.save()

        request.user.first_name = profile.first_name
        request.user.last_name = profile.last_name1
        request.user.save(update_fields=["first_name", "last_name"])

        return JsonResponse({"message": "Datos guardados.", "profile": {
            "first_name": profile.first_name,
            "last_name1": profile.last_name1,
            "last_name2": profile.last_name2,
            "display_name": profile.display_name,
            "bio": profile.bio,
        }})

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
    
