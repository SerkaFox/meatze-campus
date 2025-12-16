from rest_framework.response import Response
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.views.decorators.http import require_http_methods
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model, authenticate, login
import json, io, re, os, requests, subprocess, tempfile, logging, random
from rest_framework import status
from pathlib import Path
from functools import wraps
from .models import Curso, Enrol, UserProfile, Horario
from django.db import transaction
from django.core.cache import cache
from datetime import date, time, timedelta 
from .models import MZSetting
from django.db import transaction
from django.http import HttpResponse
from io import BytesIO
from docx import Document 
from docx.shared import Mm, Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from django.core.mail import send_mail
from .models import PendingRole
from .models import LoginPIN
from django.contrib.auth import get_user_model
from datetime import datetime
logger = logging.getLogger(__name__)
import requests
LIBREOFFICE_BIN = getattr(settings, "LIBREOFFICE_PATH", "soffice")
MEATZE_DOCX_LOGOS = getattr(settings, "MEATZE_DOCX_LOGOS", {})


User = get_user_model()

@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])
def public_cursos_for_temp(request):
    qs = Curso.objects.all().order_by("codigo")

    items = []
    for c in qs:
        items.append({
            "codigo": c.codigo,
            "titulo": c.titulo,
        })

    return Response({"items": items})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def login_password(request):
    data = {}
    try:
        if isinstance(request.data, dict):
            data.update(request.data)
    except Exception as e:
        logger.warning("login_password: error reading request.data: %s", e)
    if not data:
        try:
            raw = request.body
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode('utf-8', errors='ignore')
            raw = (raw or '').strip()
            if raw:
                data.update(json.loads(raw))
        except Exception as e:
            logger.warning(
                "login_password: cannot parse raw body as JSON: %s; body=%r",
                e, request.body[:200]
            )

    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()

    if not email or not password:
        logger.warning(
            "login_password: missing email/password. data=%r body=%r",
            data, request.body[:200]
        )
        return Response(
            {'message': 'Falta e-mail o contraseña'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2) логиним — у тебя username == email, судя по коду создания юзеров
    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response(
            {'message': 'Credenciales inválidas.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 3) создаём сессию
    login(request, user)

    # 4) собираем "me" для фронта
    me = {
        'id': user.id,
        'email': getattr(user, 'email', '') or '',
        'first_name': getattr(user, 'first_name', ''),
        'last_name': getattr(user, 'last_name', ''),
        'is_teacher': getattr(user, 'is_staff', False),  # у тебя docente = staff
        'has_password': True,
    }

    return Response({'me': me}, status=status.HTTP_200_OK)


def require_admin_token(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        token = request.GET.get("adm") or request.headers.get("X-MZ-Admin")
        expected = getattr(settings, "MEATZE_ADMIN_PASS", "MeatzeIT")

        # 👇 временный лог
        print("ADM DEBUG:", repr(token), "expected:", repr(expected))

        if token != expected:
            return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped



@csrf_exempt
@require_admin_token
def admin_ping(request):
    # Просто проверка токена
    return JsonResponse({"ok": True})


@require_admin_token
@require_http_methods(["GET"])
def admin_cursos_list(request):
    qs = Curso.objects.all().order_by("codigo")
    items = []

    for c in qs:
        # в модели modules — LIST
        modules_str = json.dumps(c.modules or [], ensure_ascii=False)

        items.append({
            "id": c.id,
            "codigo": c.codigo,
            "titulo": c.titulo,
            "modules": modules_str,   # 👈 фронт ждёт строку
            "horas": c.horas_total or 0,
        })

    return JsonResponse({"items": items})



@api_view(["GET"])
def curso_detail(request):
    """
    /meatze/v5/curso?codigo=...
    Один курс по коду.
    """
    codigo = request.query_params.get("codigo")
    if not codigo:
        return Response({"error": "codigo requerido"}, status=400)

    try:
        c = Curso.objects.get(codigo=codigo)
    except Curso.DoesNotExist:
        return Response({"error": "not_found"}, status=404)

    data = {
        "codigo": c.codigo,
        "titulo": c.titulo,
        "descripcion": c.descripcion,
        "fecha_inicio": c.fecha_inicio,
        "fecha_fin": c.fecha_fin,
    }
    return Response({"curso": data})

# ─────────────────────────────
# ADMIN · DOCENTES
# ─────────────────────────────

# вверху файла уже должны быть:
# from django.contrib.auth import get_user_model
# from .models import Curso, Enrol, UserProfile
User = get_user_model()

# ─────────────────────────────
# ADMIN · DOCENTES
# ─────────────────────────────

def _split_last_name(last_name: str):
    last_name = (last_name or "").strip()
    if not last_name:
        return "", ""
    parts = last_name.split(" ", 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


@require_admin_token
@require_http_methods(["GET"])
def admin_teachers_list(request):
    """
    GET /meatze/v5/admin/teachers
    Список преподавателей для панели Docentes.
    Берём всех пользователей с is_staff=True.
    """
    qs = (
        User.objects.filter(is_staff=True)
        .select_related("profile")
        .order_by("first_name", "last_name", "email")
    )

    items = []
    for u in qs:
        profile = getattr(u, "profile", None)

        first_name = (profile.first_name if profile and profile.first_name else u.first_name or "").strip()
        last_name1 = (profile.last_name1 if profile else "") or ""
        last_name2 = (profile.last_name2 if profile else "") or ""
        display_name = (
            profile.display_name
            if profile and profile.display_name
            else (u.get_full_name() or u.username or u.email)
        )
        bio = (profile.bio if profile else "") or ""

        items.append({
            "id": u.id,
            "email": u.email or u.username,
            "first_name": first_name,
            "last_name1": last_name1,
            "last_name2": last_name2,
            "display_name": display_name,
            "bio": bio,
        })

    return JsonResponse({"items": items})


@require_admin_token
@csrf_exempt
@require_http_methods(["GET", "POST"])
def admin_teachers_upsert(request):
    """
    GET /meatze/v5/admin/teachers   -> вернуть список (делегируем в admin_teachers_list)
    POST /meatze/v5/admin/teachers  -> создать/обновить преподавателя по email
    """
    if request.method == "GET":
        # список для таблицы снизу
        return admin_teachers_list(request)

    # ===== POST: upsert =====
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "json_invalid"}, status=400)

    print("ADMIN_TEACHERS_UPSERT payload:", repr(data))


    email = (data.get("email") or "").strip().lower()
    if not email:
        return JsonResponse({"ok": False, "message": "email_required"}, status=400)

    first_name = (data.get("first_name") or "").strip()
    last1 = (data.get("last_name1") or "").strip()
    last2 = (data.get("last_name2") or "").strip()
    bio = (data.get("bio") or "").strip()
    full_last = " ".join(p for p in [last1, last2] if p).strip()

    # пробуем найти пользователя с таким email
    existing = User.objects.filter(email=email).first()

    # если уже есть docente с таким email — считаем это ошибкой "такая почта уже есть"
    if existing and existing.is_staff:
        return JsonResponse(
            {"ok": False, "message": "email_exists"},
            status=409
        )

    with transaction.atomic():
        if existing:
            user = existing          # был alumno → делаем docente
        else:
            user = User.objects.create(email=email, username=email)

        user.first_name = first_name
        user.last_name = full_last
        user.is_staff = True         # docente = staff
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.first_name = first_name
        profile.last_name1 = last1
        profile.last_name2 = last2
        profile.display_name = (
            data.get("display_name")
            or f"{first_name} {last1}".strip()
            or email
        )
        profile.bio = bio
        profile.save()

    return JsonResponse({"ok": True, "id": user.id})

@require_admin_token
@csrf_exempt
@require_http_methods(["POST"])
def admin_teacher_update(request, user_id: int):
    """
    POST /meatze/v5/admin/teachers/<id>
    Обновление данных преподавателя.
    """
    try:
        teacher = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "message": "not_found"}, status=404)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "json_invalid"}, status=400)

    email = (data.get("email") or "").strip().lower()
    first_name = (data.get("first_name") or "").strip()
    last1 = (data.get("last_name1") or "").strip()
    last2 = (data.get("last_name2") or "").strip()
    bio = (data.get("bio") or "").strip()
    full_last = " ".join(p for p in [last1, last2] if p).strip()

    # --- проверяем конфликт по email, если его изменили ---
    current_email = (teacher.email or "").lower()
    if email and email != current_email:
        conflict = User.objects.filter(email=email).exclude(pk=teacher.pk).first()
        if conflict:
            # другой уже препод
            if conflict.is_staff:
                return JsonResponse(
                    {"ok": False, "message": "email_exists"},
                    status=409
                )
            # почта занята другим пользователем (alumno и т.п.)
            return JsonResponse(
                {"ok": False, "message": "email_in_use"},
                status=409
            )

        # если конфликта нет — обновляем email
        teacher.email = email
        if not teacher.username:
            teacher.username = email

    teacher.first_name = first_name
    teacher.last_name = full_last
    teacher.is_staff = True   # считаем staff = docente
    teacher.save()

    profile, _ = UserProfile.objects.get_or_create(user=teacher)
    profile.first_name = first_name
    profile.last_name1 = last1
    profile.last_name2 = last2
    profile.display_name = (
        data.get("display_name")
        or f"{first_name} {last1}".strip()
        or email
        or teacher.username
    )
    profile.bio = bio
    profile.save()

    return JsonResponse({"ok": True})


@require_admin_token
@csrf_exempt
@require_http_methods(["POST"])
def admin_teacher_delete(request, user_id: int):
    """
    POST /meatze/v5/admin/teachers/<id>/delete
    Убираем статус staff и чистим Enrol с ролью teacher.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"message": "not_found"}, status=404)

    # перестаёт быть docente
    user.is_staff = False
    user.save(update_fields=["is_staff"])

    # на всякий случай чистим привязки как преподавателя
    Enrol.objects.filter(user=user, role="teacher").delete()

    return JsonResponse({"ok": True})


@csrf_exempt
@require_admin_token
def admin_cursos_delete(request, curso_id):
    """
    POST /meatze/v5/admin/cursos/<id>/delete
    """
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    try:
        curso = Curso.objects.get(id=curso_id)
    except Curso.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

    curso.delete()
    return JsonResponse({"ok": True})


@require_admin_token
@csrf_exempt
@require_http_methods(["POST"])
def admin_cursos_upsert(request):
    """
    POST /meatze/v5/admin/cursos/upsert
    тело: {codigo, titulo, modules:[{name, hours}], id?}

    МОДЕЛЬ ИСПОЛЬЗУЕТ JSONField → 
    modules храним как Python list, НЕ как строку!
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"message": "json_invalid"}, status=400)

    codigo = (data.get("codigo") or "").strip()
    titulo = (data.get("titulo") or "").strip()
    modules = data.get("modules") or []

    if not codigo or not titulo:
        return JsonResponse({"message": "codigo_titulo_required"}, status=400)

    norm_modules = []
    total_horas = 0

    for m in modules:
        if not isinstance(m, dict):
            continue

        name = (m.get("name") or "").strip()
        if not name:
            continue

        hours = int(m.get("hours") or 0)
        total_horas += hours

        norm_modules.append({
            "name": name,
            "hours": hours
        })

    curso_id = data.get("id")

    if curso_id:
        curso = Curso.objects.get(id=curso_id)
    else:
        curso, _ = Curso.objects.get_or_create(codigo=codigo)

    curso.codigo = codigo
    curso.titulo = titulo
    curso.modules = norm_modules   # JSONField → кладём список, НЕ строку!
    curso.horas_total = total_horas
    curso.save()

    return JsonResponse({"ok": True, "id": curso.id, "horas": total_horas})


@require_admin_token
@csrf_exempt
@require_http_methods(["POST"])
def admin_curso_delete(request, curso_id: int):
    """
    POST /meatze/v5/admin/cursos/<id>/delete
    """
    try:
        curso = Curso.objects.get(pk=curso_id)
    except Curso.DoesNotExist:
        return JsonResponse({"message": "not_found"}, status=404)

    codigo = curso.codigo
    curso.delete()
    Enrol.objects.filter(codigo=codigo).delete()

    return JsonResponse({"ok": True})


# ─────────────────────────────
# ADMIN · ENROLMENTS (teachers per curso)
# ─────────────────────────────

@require_admin_token
@require_http_methods(["GET"])
def admin_enrolments_list(request):
    """
    GET /meatze/v5/admin/enrolments?codigo=IFCT0209&role=teacher
    Для вкладки "Asignar docentes".
    """
    codigo = (request.GET.get("codigo") or "").strip()
    role = (request.GET.get("role") or "").strip()

    qs = Enrol.objects.select_related("user").all()
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
            "email": u.email or u.username,
            "display_name": u.get_full_name() or (u.email or u.username),
            "role": e.role,
            "codigo": e.codigo,
        })

    return JsonResponse({"items": items})


@require_admin_token
@csrf_exempt
@require_http_methods(["POST"])
def admin_cursos_assign(request):
    """
    POST /meatze/v5/admin/cursos/assign
    тело: {curso_codigo: "...", teachers: ["1","2",...]}
    Обновляет список Enrol с ролью teacher для данного курса.
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"message": "json_invalid"}, status=400)

    codigo = (data.get("curso_codigo") or "").strip()
    raw_ids = data.get("teachers") or []
    if not codigo:
        return JsonResponse({"message": "codigo_required"}, status=400)

    try:
        Curso.objects.get(codigo=codigo)
    except Curso.DoesNotExist:
        return JsonResponse({"message": "curso_not_found"}, status=404)

    teacher_ids = []
    for v in raw_ids:
        try:
            teacher_ids.append(int(v))
        except (TypeError, ValueError):
            continue

    teacher_ids = list(set(teacher_ids))

    with transaction.atomic():
        # удаляем все старые привязки teacher для этого курса
        Enrol.objects.filter(codigo=codigo, role="teacher").exclude(
            user_id__in=teacher_ids
        ).delete()

        # существующие
        existing = set(
            Enrol.objects.filter(codigo=codigo, role="teacher")
            .values_list("user_id", flat=True)
        )

        for uid in teacher_ids:
            if uid in existing:
                continue
            try:
                u = User.objects.get(pk=uid)
            except User.DoesNotExist:
                continue
            Enrol.objects.create(user=u, codigo=codigo, role="teacher")

    return JsonResponse({"ok": True, "teachers": teacher_ids})


# ─────────────────────────────
# STUBS для частей, которые пока не реализованы (чтобы не было 404)
# ─────────────────────────────
@csrf_exempt
@require_admin_token
@require_http_methods(["GET", "POST"])
def admin_fixed_nonlective(request):
    """
    GET  /meatze/v5/admin/fixed-nonlective?adm=...
         → {"years": {"2025": ["01-13","08-15", ...], ...}}

    POST /meatze/v5/admin/fixed-nonlective?adm=...
         тело: {"years": {"2025": "13/01, 15/01-20/01", "2026": "10/01, 20/06"}}
    """
    CACHE_KEY = "mz_fixed_nonlective"

    if request.method == "GET":
        # 1) пробуем взять из кеша
        years = cache.get(CACHE_KEY)
        if years is None:
            # 2) если в кэше нет — берём из базы
            cfg = MZSetting.objects.filter(key="fixed_nonlective").first()
            years = (cfg.value if cfg else {}) or {}
            cache.set(CACHE_KEY, years, None)

        # гарантируем dict[str, list[str]]
        norm = {}
        for y, v in years.items():
            if isinstance(v, list):
                norm[str(y)] = v
            elif isinstance(v, str):
                norm[str(y)] = [s.strip() for s in v.split(",") if s.strip()]
            else:
                norm[str(y)] = []
        return JsonResponse({"years": norm})

    # ----- POST -----
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "json_invalid"}, status=400)

    years_raw = payload.get("years") or {}
    if not isinstance(years_raw, dict):
        return JsonResponse({"error": "years_invalid"}, status=400)

    def expand_token_to_dates(y: int, token: str) -> list[str]:
        """
        "13/01"
        "01/08-31/08"
        "10-20/09"
        → список "MM-DD"
        """
        token = token.strip()
        if not token:
            return []

        # 01/08-31/08
        m = re.match(r"^(\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})$", token)
        if m:
            d1, mo1, d2, mo2 = map(int, m.groups())
            try:
                start = date(y, mo1, d1)
                end = date(y, mo2, d2)
            except ValueError:
                return []
            if end < start:
                return []
            out = []
            cur = start
            while cur <= end:
                out.append(cur.strftime("%m-%d"))
                cur += timedelta(days=1)
            return out

        # 10-20/09
        m = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})$", token)
        if m:
            d1, d2, mo = map(int, m.groups())
            try:
                start = date(y, mo, d1)
                end = date(y, mo, d2)
            except ValueError:
                return []
            if end < start:
                return []
            out = []
            cur = start
            while cur <= end:
                out.append(cur.strftime("%m-%d"))
                cur += timedelta(days=1)
            return out

        # 13/01
        m = re.match(r"^(\d{1,2})/(\d{1,2})$", token)
        if m:
            d, mo = map(int, m.groups())
            try:
                dt = date(y, mo, d)
            except ValueError:
                return []
            return [dt.strftime("%m-%d")]

        return []

    new_years: dict[str, list[str]] = {}

    for y_str, spec in years_raw.items():
        try:
            y = int(str(y_str))
        except ValueError:
            continue

        if isinstance(spec, list):
            tokens = [str(x) for x in spec]
        else:
            tokens = [t.strip() for t in str(spec).split(",") if t.strip()]

        mmdd_set = set()
        for t in tokens:
            for mmdd in expand_token_to_dates(y, t):
                mmdd_set.add(mmdd)

        new_years[str(y)] = sorted(mmdd_set)

    # сохраняем в базу
    MZSetting.objects.update_or_create(
        key="fixed_nonlective",
        defaults={"value": new_years},
    )
    # и в кэш
    cache.set(CACHE_KEY, new_years, None)

    return JsonResponse({"ok": True, "years": new_years})

@require_admin_token
@require_http_methods(["GET"])
def admin_holidays(request, year: int):
    """
    GET /meatze/v5/admin/holidays/<year>?adm=...
    Возвращает кэшированный список праздников ES/ES-PV для фронта.

    Формат ответа:
    {
      "year": 2025,
      "items": [
        {"date": "2025-01-01", "name": "Año Nuevo"},
        ...
      ]
    }
    """

    year = int(year)
    CACHE_KEY = f"mz_holidays_{year}"

    # 1) пробуем взять из кеша
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return JsonResponse({"year": year, "items": cached})

    # 2) если нет в кеше — тянем из Nager.Date
    items = []
    try:
        r = requests.get(
            f"https://date.nager.at/api/v3/PublicHolidays/{year}/ES",
            timeout=10,
        )
        r.raise_for_status()
        raw = r.json()

        for h in raw:
            counties = h.get("counties") or []
            # если список провинций есть, берём только те, где есть ES-PV
            if counties and "ES-PV" not in counties:
                continue

            items.append({
                "date": h.get("date"),                          # YYYY-MM-DD
                "name": h.get("localName") or h.get("name", ""),  # локальное имя
            })

    except Exception as e:
        # на всякий случай не роняем фронт — просто пустой список
        print("HOLIDAYS ERROR:", e)
        items = []

    # 3) кладём в кеш, например, на сутки/месяц (можно и без TTL — на весь год)
    cache.set(CACHE_KEY, items, 60 * 60 * 24 * 30)  # 30 дней

    return JsonResponse({"year": year, "items": items})



@require_admin_token
@require_http_methods(["GET"])
def news_subscribers(request):
    """GET /meatze/v5/news/subscribers — заглушка."""
    return JsonResponse({"items": []})


@require_admin_token
@require_http_methods(["GET"])
def news_wa_inbox(request):
    """GET /meatze/v5/news/wa-inbox — заглушка."""
    return JsonResponse({"items": []})
    
@csrf_exempt
@require_http_methods(["GET", "POST"])
def curso_horario(request, codigo):
    """
    GET  /meatze/v5/curso/<codigo>/horario?tipo=curso|practica&grupo=...
    POST /meatze/v5/curso/<codigo>/horario?adm=...
         тело: {items:[...], tipo?, grupo?}
    """
    try:
        curso = Curso.objects.get(codigo=codigo)
    except Curso.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

    # ---------- READ ----------
    if request.method == "GET":
        tipo = (request.GET.get("tipo") or "").strip() or None
        grupo = (request.GET.get("grupo") or "").strip() or None

        qs = Horario.objects.filter(curso=curso).order_by("dia", "hora_inicio")

        if tipo == "curso":
            qs = qs.filter(tipo__in=["", "curso"])   # ← ключевая строка
        elif tipo:
            qs = qs.filter(tipo=tipo)

        if grupo:
            qs = qs.filter(grupo=grupo)


        items = []
        for h in qs:
            items.append({
                "id": h.id,
                "fecha": h.dia.isoformat(),
                "desde": h.hora_inicio.strftime("%H:%M"),
                "hasta": h.hora_fin.strftime("%H:%M"),
                "aula":  h.aula,
                "nota":  h.modulo or "",
                "tipo":  h.tipo or "",
                "grupo": h.grupo or "",
            })

        return JsonResponse({"codigo": codigo, "items": items})

    # ---------- WRITE ----------
    # простая проверка админ-токена (как у тебя в require_admin_token)
    token = request.GET.get("adm") or request.headers.get("X-MZ-Admin")
    expected = getattr(settings, "MEATZE_ADMIN_PASS", "MeatzeIT")
    if token != expected:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "json_invalid"}, status=400)

    items = payload.get("items", [])
    if not isinstance(items, list):
        return JsonResponse({"ok": False, "error": "items_invalid"}, status=400)

    # Текущий слой (теория / практика / группа)
    current_tipo = (payload.get("tipo") or "").strip() or (request.GET.get("tipo") or "").strip()
    current_grupo = (payload.get("grupo") or "").strip() or (request.GET.get("grupo") or "").strip()

    # запасной вариант: если фронт не положил в корень, берём из первого элемента, если есть
    if not current_tipo and items:
        current_tipo = (items[0].get("tipo") or "").strip()
    if not current_grupo and items:
        current_grupo = (items[0].get("grupo") or "").strip()


    # Удаляем ТОЛЬКО текущий слой, а не всё расписание курса
    qs = Horario.objects.filter(curso=curso)
    if current_tipo:
        qs = qs.filter(tipo=current_tipo)
    if current_grupo:
        qs = qs.filter(grupo=current_grupo)
    qs.delete()

    created = 0
    for it in items:
        fecha = it.get("fecha") or it.get("dia")
        desde = it.get("desde") or it.get("inicio")
        hasta = it.get("hasta") or it.get("fin")
        if not (fecha and desde and hasta):
            continue

        try:
            d = date.fromisoformat(str(fecha))
            hi = time.fromisoformat(str(desde))
            hf = time.fromisoformat(str(hasta))
        except ValueError:
            continue

        Horario.objects.create(
            curso=curso,
            dia=d,
            hora_inicio=hi,
            hora_fin=hf,
            modulo=it.get("nota") or it.get("modulo") or "",
            aula=it.get("aula", "") or "",
            tipo=it.get("tipo") or current_tipo or "",
            grupo=it.get("grupo") or current_grupo or "",
        )
        created += 1

    return JsonResponse({"ok": True, "count": created})


@csrf_exempt
@require_admin_token
@require_http_methods(["POST"])
def admin_curso_fecha_inicio(request, codigo: str):
    """
    POST /meatze/v5/admin/curso/<codigo>/fecha_inicio?adm=...

    тело: { "fecha": "YYYY-MM-DD" }

    Обновляет поле fecha_inicio у курса с данным código.
    """
    try:
        curso = Curso.objects.get(codigo=codigo)
    except Curso.DoesNotExist:
        return JsonResponse({"ok": False, "error": "curso_not_found"}, status=404)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "json_invalid"}, status=400)

    fecha_str = (payload.get("fecha") or "").strip()
    if not fecha_str:
        # можно либо очищать дату, либо считать ошибкой.
        # Я сделаю "очистить", чтобы было гибко:
        curso.fecha_inicio = None
        curso.save(update_fields=["fecha_inicio"])
        return JsonResponse({"ok": True, "fecha": None})

    try:
        d = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({"ok": False, "error": "fecha_invalid"}, status=400)

    curso.fecha_inicio = d
    curso.save(update_fields=["fecha_inicio"])

    return JsonResponse({"ok": True, "fecha": curso.fecha_inicio.isoformat()})
    
@api_view(["POST"])
@require_admin_token
def curso_horario_save(request, codigo):
    try:
        curso = Curso.objects.get(codigo=codigo)
    except Curso.DoesNotExist:
        return Response({"error": "not_found"}, status=404)

    items = request.data.get("items", [])
    if not isinstance(items, list):
        return Response({"error": "items_invalid"}, status=400)

    current_tipo = (request.data.get("tipo") or "").strip()
    current_grupo = (request.data.get("grupo") or "").strip()

    # запасной вариант: если фронт не положил в корень
    if not current_tipo and items:
        current_tipo = (items[0].get("tipo") or "").strip()
    if not current_grupo and items:
        current_grupo = (items[0].get("grupo") or "").strip()

    qs = Horario.objects.filter(curso=curso)
    if current_tipo:
        qs = qs.filter(tipo=current_tipo)
    if current_grupo:
        qs = qs.filter(grupo=current_grupo)
    qs.delete()

    created = 0
    for it in items:
        dia = it.get("dia") or it.get("fecha")
        inicio = it.get("inicio") or it.get("desde")
        fin = it.get("fin") or it.get("hasta")
        if not (dia and inicio and fin):
            continue

        Horario.objects.create(
            curso=curso,
            dia=dia,
            hora_inicio=inicio,
            hora_fin=fin,
            modulo=it.get("modulo") or it.get("nota") or "",
            aula=it.get("aula") or "",
            tipo=(it.get("tipo") or current_tipo or "").strip(),
            grupo=(it.get("grupo") or current_grupo or "").strip(),
        )
        created += 1

    return Response({"ok": True, "count": created})


# api/views.py
from utils.auto_horario import auto_generate_schedule
@csrf_exempt
@require_http_methods(["POST"])
@require_admin_token
def admin_auto_schedule(request, codigo):
    ...
    tipo = (payload.get("tipo") or "curso").strip()     # "curso" / "practica"
    grupo = (payload.get("grupo") or "").strip()        # для practica тут должен быть alumno_id

    # если генерируешь практику — без grupo нельзя
    if tipo == "practica" and not grupo:
        return JsonResponse({"ok": False, "error": "grupo_required_for_practica"}, status=400)

    items = auto_generate_schedule(..., grupo=(grupo or None))

    created = 0
    for it in items:
        ...
        Horario.objects.create(
            curso=curso,
            dia=d,
            hora_inicio=hi,
            hora_fin=hf,
            modulo=it.get("nota") or "",
            aula=it.get("aula") or "",
            tipo=tipo,
            grupo=grupo,
        )
        created += 1

    return JsonResponse({"ok": True, "count": created})


@api_view(["GET"])
@require_admin_token
def admin_schedule_doc(request, codigo):
    # берём реальное расписание из WP-БД
    r = requests.get(
        f"https://meatzed.zaindari.eus/meatze/v5/curso/{codigo}/horario",
        headers={"X-MZ-Admin": settings.MEATZE_ADMIN_PASS}
    )
    data = r.json()
    items = data.get("items", [])

    path = build_schedule_doc(codigo, items)

    with open(path, "rb") as f:
        resp = HttpResponse(f.read(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        resp["Content-Disposition"] = f'attachment; filename="{codigo}_horario.docx"'
        return resp


class AdminAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        admin_token = request.headers.get("X-MZ-Admin")
        if admin_token and admin_token == settings.MZ_ADMIN_TOKEN:
            request.is_admin = True
        else:
            request.is_admin = False
        return self.get_response(request)


# api/views.py
@csrf_exempt
@require_http_methods(["POST"])
@require_admin_token
def curso_horario_bulk_delete(request, codigo):
    """
    POST /meatze/v5/curso/<codigo>/horario/bulk-delete?adm=...
    {fechas:["2025-01-10", "..."]} → удаляет эти даты у данного курса
    """
    try:
        curso = Curso.objects.get(codigo=codigo)
    except Curso.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "json_invalid"}, status=400)

    raw = payload.get("fechas", [])
    if not isinstance(raw, list):
        return JsonResponse({"ok": False, "error": "fechas_invalid"}, status=400)

    from datetime import date as _date
    fechas = []
    for s in raw:
        try:
            fechas.append(_date.fromisoformat(str(s)))
        except ValueError:
            continue

    qs = Horario.objects.filter(curso=curso, dia__in=fechas)

    tipo = (payload.get("tipo") or "").strip()
    grupo = (payload.get("grupo") or "").strip()

    if tipo:
        qs = qs.filter(tipo=tipo)
    if grupo:
        qs = qs.filter(grupo=grupo)

    deleted, _ = qs.delete()
    return JsonResponse({"ok": True, "deleted": deleted})



@require_admin_token
@require_http_methods(["GET"])
def curso_alumnos(request, codigo: str):
    """
    GET /meatze/v5/curso/<codigo>/alumnos?adm=...
    Возвращает список ALUMNOS (без teachers).
    """
    enrols = (
        Enrol.objects
        .filter(codigo=codigo)
        .exclude(role="teacher")          # <-- главное: учителей убираем
        .select_related("user")
        .order_by("user__first_name", "user__last_name", "user__email")
    )

    items = []
    for e in enrols:
        u = e.user
        items.append({
            "user_id": u.id,              # <-- фронт ждёт user_id
            "id": u.id,                   # <-- можно оставить для совместимости
            "email": u.email or u.username,
            "nombre": u.get_full_name() or (u.email or u.username),
            "role": e.role,
        })

    return JsonResponse({"items": items})

    
def _inject_headers_footers(docx_path: Path):
    """
    Хедер:
      - слева маленький логотип Lanbide (1/3 ширины)
      - справа широкий логотип Euskadi (2/3 ширины, содержит 2 логотипа)

    Футер:
      - слева текст
      - справа флаг EU (без текста)
    """
    LOGOS = getattr(settings, "MEATZE_DOCX_LOGOS", {})

    doc = Document(str(docx_path))
    section = doc.sections[0]

    usable_width = section.page_width - section.left_margin - section.right_margin

    # ================= HEADER =================
    header = section.header

    # 2 колонки: 1/3 и 2/3
    h_table = header.add_table(rows=1, cols=2, width=usable_width)
    col_left_width  = int(usable_width * (1/3))
    col_right_width = int(usable_width * (2/3))
    h_table.columns[0].width = col_left_width
    h_table.columns[1].width = col_right_width

    cell_left, cell_right = h_table.rows[0].cells

    # -- Lanbide слева, поменьше
    lanbide = LOGOS.get("lanbide")
    if lanbide and Path(lanbide).exists():
        p_l = cell_left.paragraphs[0]
        p_l.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_l = p_l.add_run()
        # Сделаем маленьким, чтобы не мешал заголовку таблицы
        r_l.add_picture(lanbide, width=Cm(2.5))

    # -- Euskadi справа, крупный, занимает 2/3
    euskadi = LOGOS.get("euskadi")
    if euskadi and Path(euskadi).exists():
        p_r = cell_right.paragraphs[0]
        p_r.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_r = p_r.add_run()
        # Широкий логотип на две трети шапки
        r_r.add_picture(euskadi, width=Cm(9.5))

    # ================= FOOTER =================
    footer = section.footer

    for p in footer.paragraphs:
        p.text = ""

    # Тоже ВАЖНО: width обязателен
    f_table = footer.add_table(rows=2, cols=1, width=usable_width)
    f_table.autofit = False

    # отступ (первая строка)
    sp = f_table.rows[0].cells[0].paragraphs[0]
    sp.add_run(" ")

    # EU-флаг (вторая строка)
    eu = LOGOS.get("eu")
    if eu and Path(eu).exists():
        p = f_table.rows[1].cells[0].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.add_run().add_picture(eu, width=Cm(3.2))

    doc.save(str(docx_path))


@csrf_exempt
@require_http_methods(["POST"])
def export_docx_graphic(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "json_invalid"}, status=400)

    vacaciones = payload.get("vacaciones") or []

    def _es_dmy(ymd: str) -> str:
        # '2026-03-19' -> '19/03/2026'
        try:
            return datetime.strptime(ymd, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return ymd or ""

    def _range_es(seg: dict) -> str:
        f = _es_dmy(seg.get("from", ""))
        t = _es_dmy(seg.get("to", ""))
        if f and t and f != t:
            return f"Del {f} al {t}"
        return f or t or ""

    def _add_legend_nonlective(doc: Document, vacaciones: list):
        # Заголовок секции
        p = doc.add_paragraph("Días no lectivos / vacaciones")
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(12)

        # 1) Выходные (это фиксированная легенда)
        doc.add_paragraph("• Fines de semana (sábado y domingo) — día no lectivo")

        # 2) Сегменты vacacionesSegs (официальные+центр+ручные пропуски)
        if not vacaciones:
            doc.add_paragraph("• (Sin días no lectivos adicionales en el rango del curso)")
            return

        for seg in vacaciones:
            rango = _range_es(seg)
            motivo = (seg.get("motivo") or "").strip()
            # Пример: "Del 30/03/2026 al 06/04/2026 – Vacaciones por Jueves Santo..."
            line = f"• {rango}"
            if motivo:
                line += f" – {motivo}"
            doc.add_paragraph(line)


    html = (payload.get("html") or "").strip()
    if not html:
        return JsonResponse({"ok": False, "error": "html_required"}, status=400)

    filename = (payload.get("filename") or "calendario.docx").strip()
    if not filename.lower().endswith(".docx"):
        filename += ".docx"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        html_path = tmpdir_path / "calendario.html"
        html_path.write_text(html, encoding="utf-8")

        # 1) HTML -> DOCX через LibreOffice
        cmd = [
            LIBREOFFICE_BIN,
            "--headless", "--nologo",
            "--convert-to", "docx:MS Word 2007 XML",
            "--outdir", str(tmpdir_path),
            str(html_path),
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=tmpdir,
            timeout=120,
        )
        logger.info("LO stdout: %s", proc.stdout.decode(errors="ignore"))
        logger.info("LO stderr: %s", proc.stderr.decode(errors="ignore"))

        if proc.returncode != 0:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "soffice_failed",
                    "stdout": proc.stdout.decode(errors="ignore"),
                    "stderr": proc.stderr.decode(errors="ignore"),
                },
                status=500,
            )

        docx_files = list(tmpdir_path.glob("*.docx"))
        if not docx_files:
            return JsonResponse({"ok": False, "error": "docx_not_generated"}, status=500)

        docx_path = docx_files[0]

        # 2) Инжектируем колонтитулы с логотипами
        try:
            _inject_headers_footers(docx_path)
        except Exception as e:
            logger.exception("Failed to inject headers/footers: %s", e)
            # даже если колонтитулы не добавились — лучше всё равно вернуть файл
            # но можно и сделать ошибку, если хочешь:
            # return JsonResponse({"ok": False, "error": "branding_failed"}, status=500)
        # 3) Добавляем легенду: выходные + vacaciones (неучебные)
        try:
            vacaciones = payload.get("vacaciones") or []
            doc = Document(str(docx_path))
            _add_legend_nonlective(doc, vacaciones)
            doc.save(str(docx_path))
        except Exception as e:
            logger.exception("Failed to add nonlective legend: %s", e)

        data = docx_path.read_bytes()

    resp = HttpResponse(
        data,
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    )
    resp["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return resp

@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def request_pin(request):
    email = (request.data.get("email") or "").strip().lower()
    if not email:
        return Response({"message": "Email requerido"}, status=400)

    # генерируем 6 цифр
    pin = f"{random.randint(0, 999999):06d}"

    # сохраняем
    LoginPIN.objects.create(email=email, pin=pin)

    # создаём пользователя, если нет
    user, created = User.objects.get_or_create(email=email, defaults={"username": email})


    PendingRole.objects.get_or_create(
        user=user,
        email=email,
        status="pending",
        defaults={"requested_role": "unknown"},
    )


    # отправляем письмо
    send_mail(
        subject="Tu PIN de acceso a MEATZE",
        message=f"Tu código PIN es: {pin}\nVálido durante 10 minutos.",
        from_email="no-reply@meatze.eus",
        recipient_list=[email],
        fail_silently=False,
    )

    return Response({"ok": True, "message": "PIN enviado"})
