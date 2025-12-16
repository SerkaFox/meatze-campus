# api/auth_views.py
import random
from datetime import timedelta
from django.contrib.auth import get_user_model, authenticate, login, logout

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import LoginPIN, UserProfile 
from api.models import PendingRole 

User = get_user_model()
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)

def get_django_request(req):
    """
    DRF Request -> Django HttpRequest
    """
    return getattr(req, "_request", req)

# --- вспомогалка для ответа "me" ---
def build_me(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        # docente?
        "is_teacher": bool(getattr(user, "is_staff", False)),
        # есть ли пароль
        "has_password": bool(user.has_usable_password()),
    }


# 1) REQUEST PIN  -------------------------------------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])   # без SessionAuthentication → без CSRF от DRF
def request_pin(request):
    """
    POST /meatze/v5/auth/request_pin
    { "email": "..." }

    Создаёт 6-значный PIN и отправляет на почту.
    PIN действует 10 минут.
    """
    email = (request.data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return Response({"message": "E-mail inválido"}, status=status.HTTP_400_BAD_REQUEST)

    # 6-значный PIN
    code = f"{random.randint(0, 999999):06d}"

    # очищаем старые PIN для этого email
    LoginPIN.objects.filter(email=email).delete()
    LoginPIN.objects.create(email=email, pin=code)

    # ── отправка письма ──
    subject = "Tu PIN de acceso a MEATZE"
    message = (
        f"Hola,\n\n"
        f"Tu código de acceso a MEATZE es: {code}\n\n"
        f"Es válido durante 10 minutos.\n\n"
        f"Un saludo,\n"
        f"Equipo MEATZE"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER

    try:
        send_mail(subject, message, from_email, [email], fail_silently=False)
    except Exception as e:
        # лог — по желанию
        print("EMAIL ERROR:", e)
        return Response(
            {"ok": False, "message": "No se pudo enviar el PIN."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({"ok": True, "message": "PIN enviado (válido 10 min)."})


# 2) VERIFY PIN  --------------------------------------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])   # сами работаем с сессией
def verify_pin(request):
    """
    POST /meatze/v5/auth/verify_pin
    { "email": "...", "pin": "123456" }

    Проверяет PIN, создаёт/находит пользователя, логинит через сессию,
    возвращает {me:{...}}.
    """
    email = (request.data.get("email") or "").strip().lower()
    pin = (request.data.get("pin") or "").strip()

    if not email or "@" not in email:
        return Response({"message": "E-mail inválido"}, status=status.HTTP_400_BAD_REQUEST)
    if len(pin) != 6 or not pin.isdigit():
        return Response({"message": "PIN debe tener 6 dígitos"}, status=status.HTTP_400_BAD_REQUEST)

    # ищем PIN
    try:
        rec = LoginPIN.objects.get(email=email, pin=pin)
    except LoginPIN.DoesNotExist:
        return Response(
            {"message": "PIN incorrecto o caducado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # проверка на 10 минут
    if rec.created_at < timezone.now() - timedelta(minutes=10):
        rec.delete()
        return Response(
            {"message": "PIN incorrecto o caducado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ищем/создаём пользователя
    user = User.objects.filter(email=email).first()
    if not user:
        # создаём простого "alumno"
        user = User.objects.create_user(
            username=email,
            email=email,
            password=None,      # без пароля, будет логин через PIN
        )

    # логиним по сессии (ВАЖНО: через HttpRequest)
    django_request = get_django_request(request)
    login(django_request, user)
    try:
        obj, created = PendingRole.objects.get_or_create(
            user=user,
            email=user.email,
            status="pending",
            defaults={"requested_role": "unknown"},
        )
        print("PENDING:", "created" if created else "exists", obj.id, obj.email)
    except Exception as e:
        print("PENDING ERROR:", repr(e))


    me = build_me(user)
    return Response({"me": me}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])   # работаем сами с сессией
def set_password(request):
    """
    Два режима:

    1) Первый вход по PIN:
       body = { "password": "...", "email": "...", "pin": "123456" }

    2) Смена пароля из кабинета (Datos personales):
       body = { "password": "..." }   # берём request.user
    """
    password = (request.data.get("password") or "").strip()
    if len(password) < 6:
        return Response(
            {"message": "Contraseña demasiado corta (mín. 6)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    django_request = get_django_request(request)
    email = (request.data.get("email") or "").strip().lower()
    pin   = (request.data.get("pin") or "").strip()

    # ─────────────────────────
    # РЕЖИМ 1: email + pin → как раньше
    # ─────────────────────────
    if email and pin:
        if "@" not in email:
            return Response(
                {"message": "E-mail inválido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(pin) != 6 or not pin.isdigit():
            return Response(
                {"message": "PIN debe tener 6 dígitos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        pin_obj = (
            LoginPIN.objects
            .filter(
                email=email,
                pin=pin,
                created_at__gte=now - timedelta(minutes=15),
            )
            .order_by("-created_at")
            .first()
        )

        if not pin_obj:
            return Response(
                {"message": "PIN inválido o caducado."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.set_password(password)
        user.save()

        # очищаем все PIN'ы на этот email
        LoginPIN.objects.filter(email=email).delete()

        # на всякий случай перелогиниваем
        login(django_request, user)

        me = build_me(user)
        return Response({"ok": True, "me": me}, status=status.HTTP_200_OK)

    # ─────────────────────────
    # РЕЖИМ 2: уже залогинен, меняем пароль по сессии
    # ─────────────────────────
    user = getattr(django_request, "user", None)
    if user and user.is_authenticated:
        user.set_password(password)
        user.save()

        # чтобы сессия не отвалилась — перелогиниваем
        login(django_request, user)

        me = build_me(user)
        return Response({"ok": True, "me": me}, status=status.HTTP_200_OK)

    # ни email+pin, ни залогиненного пользователя
    return Response(
        {"message": "Autenticación requerida."},
        status=status.HTTP_401_UNAUTHORIZED,
    )

# 4) LOGOUT  ------------------------------------------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def logout_view(request):
    """
    POST /meatze/v5/auth/logout
    """
    django_request = get_django_request(request)
    logout(django_request)
    return Response({"ok": True})



# ─────────────────────────
# ЛОГИН ПО ПАРОЛЮ (кнопка Entrar)
# ─────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])   # работаем через login(), без DRF-авторизаций
def login_password(request):
    email = (request.data.get('email') or '').strip().lower()
    password = (request.data.get('password') or '').strip()

    if not email or not password:
        return Response(
            {'message': 'Falta e-mail o contraseña'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1) пробуем найти юзера по email
    user_obj = User.objects.filter(email__iexact=email).first()

    user = None
    if user_obj:
        user = authenticate(request, username=user_obj.username, password=password)

    # 2) fallback: вдруг username уже = email
    if user is None:
        user = authenticate(request, username=email, password=password)

    if user is None:
        return Response(
            {'message': 'Credenciales inválidas.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    django_request = get_django_request(request)
    login(django_request, user)
    me = build_me(user)


    return Response({'me': me}, status=status.HTTP_200_OK)

@csrf_exempt
@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])  # не используем DRF-авторизации, читаем сессию сами
def me_view(request):
    """
    GET /meatze/v5/me

    Возвращает текущего юзера по сессии:
    { "me": { ... } } или { "me": null }, если не залогинен.
    """
    django_request = get_django_request(request)
    u = getattr(django_request, "user", None)

    if not u or not u.is_authenticated:
        return Response({"me": None}, status=status.HTTP_200_OK)

    me = build_me(u)
    return Response({"me": me}, status=status.HTTP_200_OK)
