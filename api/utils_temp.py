import random
import re
import unicodedata

from django.contrib.auth import get_user_model
from .models import Enrol
from panel.models import Curso, TempAccess

User = get_user_model()

from api.models import Enrol   # обязательно!
from panel.models import Curso
from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication без принудительной проверки CSRF.
    Используется там, где мы доверяем сессии и не хотим заморачиваться с CSRF-токенами.
    """
    def enforce_csrf(self, request):
        return  # просто ничего не делаем

def is_teacher(user):
    """
    Во ВСЕХ новых местах считаем docente по простой логике:
    1) user.is_staff == True → считается преподавателем
    2) есть профиль с флагом is_teacher → преподаватель
    3) есть хотя бы один Enrol с role='teacher' → тоже преподаватель
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False

    # 1) staff == docente (как у тебя в панели)
    if getattr(user, "is_staff", False):
        return True

    # 2) профиль
    profile = getattr(user, "profile", None)
    if profile is not None and getattr(profile, "is_teacher", False):
        return True

    # 3) хотя бы один курс, где он учитель
    return Enrol.objects.filter(user=user, role="teacher").exists()


def ensure_teacher_of_course(user, curso: Curso) -> bool:
    """
    Проверяем, что user — преподаватель КОНКРЕТНО ЭТОГО курса.
    Staff пускаем автоматически.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False

    # staff имеет право на все курсы
    if getattr(user, "is_staff", False):
        return True

    return Enrol.objects.filter(
        user=user,
        codigo=curso.codigo,
        role="teacher",
    ).exists()




def two_digit_code():
    return f"{random.randint(0, 99):02d}"


def local_from_name(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s or "alumno"


def domain_from_course(code: str) -> str:
    s = unicodedata.normalize("NFKD", code or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s or "curso"


