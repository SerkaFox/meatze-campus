import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User


def serialize_me(user):
    if not user.is_authenticated:
        return None
    # потом сюда добавим поля типа is_teacher, has_password и т.п.
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.get_full_name() or user.username,
        "is_teacher": False,
        "has_password": True,
        "rest_nonce": "",  # в Django нам не нужен, но фронт его не сломается
    }


@csrf_exempt
def login_password(request):
    if request.method != "POST":
        return JsonResponse({"message": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"message": "JSON inválido"}, status=400)

    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return JsonResponse({"message": "Falta e-mail o contraseña"}, status=400)

    # В простом варианте считаем, что username = email
    try:
        user = User.objects.get(email__iexact=email)
        username = user.username
    except User.DoesNotExist:
        # можно сразу фейлить
        return JsonResponse({"message": "Credenciales inválidas."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"message": "Credenciales inválidas."}, status=400)

    login(request, user)  # создаём сессию

    return JsonResponse({"me": serialize_me(user)})


def me_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"logged_in": False}, status=200)
    return JsonResponse({
        "logged_in": True,
        "me": serialize_me(request.user),
    })
