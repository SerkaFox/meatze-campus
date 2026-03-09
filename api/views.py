# api/views.py

import json
import io
import re
import os
import requests
import subprocess
import tempfile
import logging
import random
from datetime import date, time, timedelta, datetime
from io import BytesIO
from pathlib import Path
from functools import wraps

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.contrib.auth import get_user_model, authenticate, login

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework import status

def privacy_policy(request):
    return render(request, "legal/privacy.html")


def terms_of_service(request):
    return render(request, "legal/terms.html")

from .models import (
    Curso, Enrol, UserProfile, Horario, PendingRole, LoginPIN, MZSetting
)

from .decorators import require_admin_token

from panel.models import (
    CursoFile, CursoPhysicalConfig, MaterialDownload, MaterialReceipt
)
from panel.views import PHYSICAL_ITEMS

# ✅ DOCX export вынесен в отдельный файл
from .docx_export import export_docx_graphic

logger = logging.getLogger(__name__)
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

    user = authenticate(request, username=email, password=password)
    if user is None:
        return Response(
            {'message': 'Credenciales inválidas.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    login(request, user)

    me = {
        'id': user.id,
        'email': getattr(user, 'email', '') or '',
        'first_name': getattr(user, 'first_name', ''),
        'last_name': getattr(user, 'last_name', ''),
        'is_teacher': getattr(user, 'is_staff', False),
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
    return JsonResponse({"ok": True})


@require_admin_token
@require_http_methods(["GET"])
def admin_cursos_list(request):
    qs = Curso.objects.all().order_by("codigo")
    items = []

    for c in qs:
        modules_str = json.dumps(c.modules or [], ensure_ascii=False)

        items.append({
            "id": c.id,
            "codigo": c.codigo,
            "titulo": c.titulo,
            "modules": modules_str,
            "horas": c.horas_total or 0,
            "tipo_formacion": c.tipo_formacion,
        })

    return JsonResponse({"items": items})


def _admin_can_access_course(request, curso: Curso) -> bool:
    return True


@require_admin_token
@require_http_methods(["GET"])
def admin_material_status(request):
    codigo = (request.GET.get("codigo") or "").strip().upper()
    if not codigo:
        return JsonResponse({"ok": False, "error": "codigo required"}, status=400)

    curso = get_object_or_404(Curso, codigo=codigo)

    if not _admin_can_access_course(request, curso):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    cfg = CursoPhysicalConfig.objects.filter(curso=curso).only("enabled_keys").first()
    physical_keys = (cfg.enabled_keys if cfg else []) or []
    total_phys = len(physical_keys)

    visible_files_qs = (
        CursoFile.objects.filter(curso=curso)
        .filter(
            Q(tipo=CursoFile.TIPO_ALUMNOS) |
            (Q(share_alumnos=True) & Q(tipo__in=[CursoFile.TIPO_DOCENTES, CursoFile.TIPO_PRIVADO]))
        )
        .only("id", "title", "file")
    )

    visible_ids = list(visible_files_qs.values_list("id", flat=True))
    total_visible = len(visible_ids)

    if total_visible == 0 and total_phys == 0:
        return JsonResponse({
            "ok": True,
            "codigo": curso.codigo,
            "total_files": 0,
            "total_phys": 0,
            "items": {}
        })

    dl_counts = dict(
        MaterialDownload.objects.filter(file_id__in=visible_ids)
        .values("alumno_id").annotate(c=Count("id"))
        .values_list("alumno_id", "c")
    )

    rc_counts = dict(
        MaterialReceipt.objects.filter(curso=curso, item_key__in=physical_keys)
        .values("alumno_id").annotate(c=Count("id"))
        .values_list("alumno_id", "c")
    )

    file_map = {}
    for f in visible_files_qs:
        filename = ""
        try:
            filename = getattr(f.file, "name", "") or ""
            filename = filename.rsplit("/", 1)[-1]
        except Exception:
            filename = ""
        file_map[f.id] = (f.title or filename or f"#{f.id}")

    dl_detail = {}
    dl_rows = (
        MaterialDownload.objects
        .filter(file_id__in=visible_ids)
        .values_list("alumno_id", "file_id")
    )
    for aid, fid in dl_rows:
        dl_detail.setdefault(aid, []).append(file_map.get(fid, f"#{fid}"))

    label_by_key = {it["key"]: it["label"] for it in PHYSICAL_ITEMS}
    rc_detail = {}
    rc_rows = (
        MaterialReceipt.objects
        .filter(curso=curso, item_key__in=physical_keys)
        .values_list("alumno_id", "item_label", "item_key")
    )
    for aid, item_label, item_key in rc_rows:
        label = (item_label or "").strip() or label_by_key.get(item_key, item_key)
        rc_detail.setdefault(aid, []).append(label)

    all_ids = set(dl_counts) | set(rc_counts) | set(dl_detail) | set(rc_detail)

    def _uniq(seq):
        seen = set()
        out = []
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    items = {}
    for aid in all_ids:
        items[str(aid)] = {
            "d": int(dl_counts.get(aid, 0)),
            "r": int(rc_counts.get(aid, 0)),
            "dl": _uniq(dl_detail.get(aid, [])),
            "rc": _uniq(rc_detail.get(aid, [])),
        }

    return JsonResponse({
        "ok": True,
        "codigo": curso.codigo,
        "total_files": total_visible,
        "total_phys": total_phys,
        "items": items,
    })


@api_view(["GET"])
def curso_detail(request):
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


def acceder(request):
    tab = (request.GET.get("tab") or "login").strip().lower()

    if request.user.is_authenticated and tab == "profile":
        return render(request, "acceder.html", {})

    if request.user.is_authenticated and tab in ("", "login"):
        return redirect("/alumno/")

    return render(request, "acceder.html", {})


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
    qs = (
        User.objects.filter(is_staff=True)
        .select_related("profile")
        .order_by("first_name", "last_name", "email")
    )

    users = list(qs)
    user_ids = [u.id for u in users]

    enrols = (
        Enrol.objects
        .filter(user_id__in=user_ids, role="teacher")
        .values_list("user_id", "codigo")
    )

    by_user = {}
    codigos = set()
    for uid, codigo in enrols:
        codigo = (codigo or "").strip().upper()
        if not codigo:
            continue
        by_user.setdefault(uid, []).append(codigo)
        codigos.add(codigo)

    titulo_by_codigo = dict(
        Curso.objects.filter(codigo__in=list(codigos))
        .values_list("codigo", "titulo")
    )

    items = []
    for u in users:
        profile = getattr(u, "profile", None)
        wa = (profile.wa if profile else "") or ""
        first_name = (profile.first_name if profile and profile.first_name else u.first_name or "").strip()
        last_name1 = (profile.last_name1 if profile else "") or ""
        last_name2 = (profile.last_name2 if profile else "") or ""
        display_name = (
            profile.display_name
            if profile and profile.display_name
            else (u.get_full_name() or u.username or u.email)
        )

        cods = by_user.get(u.id, []) or []
        cursos = [{"codigo": c, "titulo": (titulo_by_codigo.get(c) or "")} for c in sorted(set(cods))]

        items.append({
            "id": u.id,
            "email": u.email or u.username,
            "wa": wa,
            "first_name": first_name,
            "last_name1": last_name1,
            "last_name2": last_name2,
            "display_name": display_name,
            "cursos": cursos,
        })

    return JsonResponse({"items": items})


@require_admin_token
@csrf_exempt
@require_http_methods(["GET", "POST"])
def admin_teachers_upsert(request):
    if request.method == "GET":
        return admin_teachers_list(request)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "json_invalid"}, status=400)

    user_id = data.get("id")
    email = (data.get("email") or "").strip().lower()
    if not email:
        return JsonResponse({"ok": False, "message": "email_required"}, status=400)

    first_name = (data.get("first_name") or "").strip()
    last1 = (data.get("last_name1") or "").strip()
    last2 = (data.get("last_name2") or "").strip()
    bio  = (data.get("bio") or "").strip()
    wa   = (data.get("wa") or "").strip()
    full_last = " ".join(p for p in [last1, last2] if p).strip()

    with transaction.atomic():
        user = None

        if user_id:
            user = User.objects.filter(pk=int(user_id)).first()
            if not user:
                return JsonResponse({"ok": False, "message": "not_found"}, status=404)

            current_email = ((user.email or user.username or "")).strip().lower()

            if email and email != current_email:
                return JsonResponse({
                    "ok": False,
                    "message": "email_change_forbidden",
                    "detail": (
                        "No se puede cambiar el e-mail de un docente existente. "
                        "Elimínalo y vuelve a añadirlo con el nuevo e-mail."
                    )
                }, status=409)

        if not user:
            user = User.objects.filter(username__iexact=email).first()

            if not user:
                user = User.objects.filter(email__iexact=email).first()

            if user and (user.username or "").strip().lower() != email:
                return JsonResponse({
                    "ok": False,
                    "message": "username_mismatch",
                    "detail": (
                        "Ese e-mail ya existe en el sistema con otro identificador. "
                        "Para cambiarlo, elimina el usuario anterior (purge) y vuelve a crearlo."
                    )
                }, status=409)

            if not user:
                try:
                    user = User.objects.create(username=email, email=email)
                except IntegrityError:
                    user = User.objects.filter(username__iexact=email).first()
                    if not user:
                        raise

            if (user.email or "").strip().lower() != email:
                user.email = email

        user.first_name = first_name
        user.last_name = full_last
        user.is_staff = True
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.first_name = first_name
        profile.last_name1 = last1
        profile.last_name2 = last2
        profile.bio = bio
        profile.wa = wa
        if (data.get("display_name") or "").strip():
            profile.display_name = (data.get("display_name") or "").strip()
        profile.is_teacher = True if hasattr(profile, "is_teacher") else getattr(profile, "is_teacher", False)
        profile.save()

    return JsonResponse({"ok": True, "id": user.id})


@require_admin_token
@csrf_exempt
@require_http_methods(["POST"])
def admin_teacher_update(request, user_id: int):
    try:
        teacher = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "message": "not_found"}, status=404)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "json_invalid"}, status=400)

    email = (data.get("email") or "").strip().lower()
    wa  = (data.get("wa") or "").strip()
    first_name = (data.get("first_name") or "").strip()
    last1 = (data.get("last_name1") or "").strip()
    last2 = (data.get("last_name2") or "").strip()
    bio = (data.get("bio") or "").strip()
    full_last = " ".join(p for p in [last1, last2] if p).strip()

    current_email = (teacher.email or "").lower()
    if email and email != current_email:
        conflict = User.objects.filter(email=email).exclude(pk=teacher.pk).first()
        if conflict:
            if conflict.is_staff:
                return JsonResponse({"ok": False, "message": "email_exists"}, status=409)
            return JsonResponse({"ok": False, "message": "email_in_use"}, status=409)

        teacher.email = email
        if not teacher.username:
            teacher.username = email

    teacher.first_name = first_name
    teacher.last_name = full_last
    teacher.is_staff = True
    teacher.save()

    profile, _ = UserProfile.objects.get_or_create(user=teacher)
    profile.first_name = first_name
    profile.wa = wa
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
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"message": "not_found"}, status=404)

    user.is_staff = False
    user.save(update_fields=["is_staff"])

    Enrol.objects.filter(user=user, role="teacher").delete()

    return JsonResponse({"ok": True})


@csrf_exempt
@require_admin_token
def admin_cursos_delete(request, curso_id):
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
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"message": "json_invalid"}, status=400)

    codigo = (data.get("codigo") or "").strip().upper()
    titulo = (data.get("titulo") or "").strip()
    modules = data.get("modules") or []
    tipo_formacion = (data.get("tipo_formacion") or "").strip().lower()

    clone_from = (data.get("clone_from") or "").strip().upper()

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
        if hours < 0:
            hours = 0
        total_horas += hours
        norm_modules.append({"name": name, "hours": hours})

    curso_id = data.get("id")
    creating = False

    with transaction.atomic():
        if curso_id:
            try:
                curso = Curso.objects.get(id=curso_id)
            except Curso.DoesNotExist:
                curso = Curso.objects.filter(codigo=codigo).first()
                if not curso:
                    curso = Curso(codigo=codigo)
                    creating = True
        else:
            curso = Curso.objects.filter(codigo=codigo).first()
            if not curso:
                curso = Curso(codigo=codigo)
                creating = True

        curso.codigo = codigo
        curso.titulo = titulo
        curso.modules = norm_modules
        curso.horas_total = total_horas
        curso.tipo_formacion = tipo_formacion
        curso.save()

        cloned_files = 0
        if creating and clone_from and clone_from != codigo:
            src = Curso.objects.filter(codigo=clone_from).first()
            if src:
                src_qs = (CursoFile.objects
                          .filter(curso=src)
                          .only("tipo", "module_key", "title", "file", "size", "ext",
                                "share_alumnos", "uploaded_by", "folder_path"))

                batch = []
                for f in src_qs:
                    nf = CursoFile(
                        curso=curso,
                        uploaded_by=f.uploaded_by,
                        tipo=f.tipo,
                        module_key=f.module_key,
                        title=f.title,
                        size=f.size,
                        ext=f.ext,
                        share_alumnos=f.share_alumnos,
                        folder_path=f.folder_path,
                    )
                    nf.file.name = f.file.name
                    batch.append(nf)

                if batch:
                    CursoFile.objects.bulk_create(batch)
                    cloned_files = len(batch)

    return JsonResponse({
        "ok": True,
        "id": curso.id,
        "horas": total_horas,
        "tipo_formacion": curso.tipo_formacion,
        "cloned_files": cloned_files,
    })


@require_admin_token
@csrf_exempt
@require_http_methods(["POST"])
def admin_curso_delete(request, curso_id: int):
    try:
        curso = Curso.objects.get(pk=curso_id)
    except Curso.DoesNotExist:
        return JsonResponse({"message": "not_found"}, status=404)

    codigo = curso.codigo
    curso.delete()
    Enrol.objects.filter(codigo=codigo).delete()

    return JsonResponse({"ok": True})


@require_admin_token
@require_http_methods(["GET"])
def admin_enrolments_list(request):
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
        Enrol.objects.filter(codigo=codigo, role="teacher").exclude(
            user_id__in=teacher_ids
        ).delete()

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


@csrf_exempt
@require_admin_token
@require_http_methods(["GET", "POST"])
def admin_fixed_nonlective(request):
    CACHE_KEY = "mz_fixed_nonlective"

    if request.method == "GET":
        years = cache.get(CACHE_KEY)
        if years is None:
            cfg = MZSetting.objects.filter(key="fixed_nonlective").first()
            years = (cfg.value if cfg else {}) or {}
            cache.set(CACHE_KEY, years, None)

        norm = {}
        for y, v in (years or {}).items():
            if isinstance(v, list):
                norm[str(y)] = [str(x).strip() for x in v if str(x).strip()]
            elif isinstance(v, str):
                norm[str(y)] = [s.strip() for s in v.split(",") if s.strip()]
            else:
                norm[str(y)] = []
        return JsonResponse({"years": norm})

    try:
        raw = (request.body or b"").decode("utf-8").strip()
        payload = json.loads(raw) if raw else {}
    except Exception:
        return JsonResponse({"error": "invalid_json"}, status=400)

    years_raw = payload.get("years") or {}
    if not isinstance(years_raw, dict):
        return JsonResponse({"error": "years_invalid"}, status=400)

    def expand_token_to_dates(y: int, token: str) -> list[str]:
        token = token.strip()
        if not token:
            return []

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
            out, cur = [], start
            while cur <= end:
                out.append(cur.strftime("%m-%d"))
                cur += timedelta(days=1)
            return out

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
            out, cur = [], start
            while cur <= end:
                out.append(cur.strftime("%m-%d"))
                cur += timedelta(days=1)
            return out

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

    MZSetting.objects.update_or_create(
        key="fixed_nonlective",
        defaults={"value": new_years},
    )
    cache.set(CACHE_KEY, new_years, None)

    return JsonResponse({"ok": True, "years": new_years})


@require_admin_token
@require_http_methods(["GET"])
def admin_holidays(request, year: int):
    year = int(year)
    CACHE_KEY = f"mz_holidays_{year}"

    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return JsonResponse({"year": year, "items": cached})

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
            if counties and "ES-PV" not in counties:
                continue

            items.append({
                "date": h.get("date"),
                "name": h.get("localName") or h.get("name", ""),
            })

    except Exception as e:
        print("HOLIDAYS ERROR:", e)
        items = []

    cache.set(CACHE_KEY, items, 60 * 60 * 24 * 30)

    return JsonResponse({"year": year, "items": items})


@require_admin_token
@require_http_methods(["GET"])
def news_subscribers(request):
    return JsonResponse({"items": []})


@require_admin_token
@require_http_methods(["GET"])
def news_wa_inbox(request):
    return JsonResponse({"items": []})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def curso_horario(request, codigo):
    try:
        curso = Curso.objects.get(codigo=codigo)
    except Curso.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

    if request.method == "GET":
        tipo = (request.GET.get("tipo") or "").strip() or None
        grupo = (request.GET.get("grupo") or "").strip() or None

        qs = Horario.objects.filter(curso=curso).order_by("dia", "hora_inicio")

        if tipo == "curso":
            qs = qs.filter(Q(tipo__isnull=True) | Q(tipo="") | Q(tipo="curso"))
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

    current_tipo = (payload.get("tipo") or "").strip() or (request.GET.get("tipo") or "").strip()
    current_grupo = (payload.get("grupo") or "").strip() or (request.GET.get("grupo") or "").strip()

    if not current_tipo and items:
        current_tipo = (items[0].get("tipo") or "").strip()
    if not current_grupo and items:
        current_grupo = (items[0].get("grupo") or "").strip()

    qs = Horario.objects.filter(curso=curso)

    if current_tipo == "curso" or current_tipo == "":
        qs = qs.filter(Q(tipo__isnull=True) | Q(tipo="") | Q(tipo="curso"))
    elif current_tipo:
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

    if not current_tipo and items:
        current_tipo = (items[0].get("tipo") or "").strip()
    if not current_grupo and items:
        current_grupo = (items[0].get("grupo") or "").strip()

    qs = Horario.objects.filter(curso=curso)

    if current_tipo == "curso" or current_tipo == "":
        qs = qs.filter(Q(tipo__isnull=True) | Q(tipo="") | Q(tipo="curso"))
    elif current_tipo:
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


@csrf_exempt
@require_http_methods(["POST"])
@require_admin_token
def curso_horario_bulk_delete(request, codigo):
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

    if tipo == "curso" or tipo == "":
        qs = qs.filter(Q(tipo__isnull=True) | Q(tipo="") | Q(tipo="curso"))
    elif tipo:
        qs = qs.filter(tipo=tipo)

    if grupo:
        qs = qs.filter(grupo=grupo)

    deleted, _ = qs.delete()
    return JsonResponse({"ok": True, "deleted": deleted})


@require_admin_token
@require_http_methods(["GET"])
def curso_alumnos(request, codigo: str):
    enrols = (
        Enrol.objects
        .filter(codigo=codigo)
        .exclude(role="teacher")
        .select_related("user")
        .order_by("user__first_name", "user__last_name", "user__email")
    )

    items = []
    for e in enrols:
        u = e.user
        items.append({
            "user_id": u.id,
            "id": u.id,
            "email": u.email or u.username,
            "nombre": u.get_full_name() or (u.email or u.username),
            "role": e.role,
        })

    return JsonResponse({"items": items})


@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def request_pin(request):
    email = (request.data.get("email") or "").strip().lower()
    if not email:
        return Response({"message": "Email requerido"}, status=400)

    pin = f"{random.randint(0, 999999):06d}"
    LoginPIN.objects.create(email=email, pin=pin)

    user, created = User.objects.get_or_create(email=email, defaults={"username": email})

    PendingRole.objects.get_or_create(
        user=user,
        email=email,
        status="pending",
        defaults={"requested_role": "unknown"},
    )

    send_mail(
        subject="Tu PIN de acceso a MEATZE",
        message=f"Tu código PIN es: {pin}\nVálido durante 10 minutos.",
        from_email="no-reply@meatze.eus",
        recipient_list=[email],
        fail_silently=False,
    )

    return Response({"ok": True, "message": "PIN enviado"})
    
def _effective_nonlective_years(curso: Curso) -> dict[str, list[str]]:
    if getattr(curso, "use_global_nonlective", True):
        return _get_global_nonlective_years()
    return _normalize_years_mmdd(curso.nonlective_years or {})

@require_admin_token
@require_http_methods(["GET"])
def admin_curso_nonlective_effective(request, codigo: str):
    curso = get_object_or_404(Curso, codigo=(codigo or "").strip().upper())
    years = _effective_nonlective_years(curso)
    return JsonResponse({"ok": True, "codigo": curso.codigo, "years": years})
    
@require_admin_token
@csrf_exempt
@require_http_methods(["GET", "POST"])
def admin_curso_nonlective(request, codigo: str):
    curso = get_object_or_404(Curso, codigo=(codigo or "").strip().upper())

    if request.method == "GET":
        global_years = _get_global_nonlective_years()

        # курс хранит mm-dd list, но вдруг там старые строки — нормализуем на лету
        course_years = curso.nonlective_years or {}
        course_years = _normalize_years_mmdd(course_years)

        return JsonResponse({
            "ok": True,
            "codigo": curso.codigo,
            "use_global": bool(getattr(curso, "use_global_nonlective", True)),
            "years": course_years,
            "global_years": global_years,
        })

    # POST
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "json_invalid"}, status=400)

    use_global = payload.get("use_global")
    years_raw = payload.get("years")

    if use_global is None:
        # можно не присылать — тогда не меняем
        use_global = getattr(curso, "use_global_nonlective", True)
    else:
        use_global = bool(use_global)

    if years_raw is None:
        years_norm = _normalize_years_mmdd(curso.nonlective_years or {})
    else:
        years_norm = _normalize_years_mmdd(years_raw)

    # сохраняем
    curso.use_global_nonlective = use_global
    curso.nonlective_years = years_norm
    curso.save(update_fields=["use_global_nonlective", "nonlective_years"])

    return JsonResponse({
        "ok": True,
        "codigo": curso.codigo,
        "use_global": curso.use_global_nonlective,
        "years": curso.nonlective_years,
    })
    
def _normalize_years_mmdd(years_raw) -> dict[str, list[str]]:
    if not isinstance(years_raw, dict):
        return {}

    def is_mmdd(s: str) -> bool:
        return bool(re.match(r"^\d{2}-\d{2}$", s or ""))

    def expand_token_to_dates(y: int, token: str) -> list[str]:
        token = (token or "").strip()
        if not token:
            return []

        # DD/MM - DD/MM
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
            out, cur = [], start
            while cur <= end:
                out.append(cur.strftime("%m-%d"))
                cur += timedelta(days=1)
            return out

        # DD-DD/MM
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
            out, cur = [], start
            while cur <= end:
                out.append(cur.strftime("%m-%d"))
                cur += timedelta(days=1)
            return out

        # DD/MM
        m = re.match(r"^(\d{1,2})/(\d{1,2})$", token)
        if m:
            d, mo = map(int, m.groups())
            try:
                dt = date(y, mo, d)
            except ValueError:
                return []
            return [dt.strftime("%m-%d")]

        # MM-DD (уже норм)
        if is_mmdd(token):
            return [token]

        return []

    out: dict[str, list[str]] = {}
    for y_str, spec in years_raw.items():
        try:
            y = int(str(y_str))
        except ValueError:
            continue

        # вход может быть:
        # 1) list ["03-24","03-25"]  или ["24/03","25/03","01/04-05/04"]
        # 2) string "24/03, 01/04-05/04"
        if isinstance(spec, list):
            tokens = [str(x).strip() for x in spec if str(x).strip()]
        else:
            tokens = [t.strip() for t in str(spec).split(",") if t.strip()]

        mmdd_set = set()
        for t in tokens:
            for mmdd in expand_token_to_dates(y, t):
                mmdd_set.add(mmdd)

        out[str(y)] = sorted(mmdd_set)

    return out
    
def _get_global_nonlective_years() -> dict[str, list[str]]:
    cfg = MZSetting.objects.filter(key="fixed_nonlective").first()
    years = (cfg.value if cfg else {}) or {}
    out: dict[str, list[str]] = {}
    for y, v in years.items():
        if isinstance(v, list):
            out[str(y)] = [str(x).strip() for x in v if str(x).strip()]
        elif isinstance(v, str):
            # на всякий, если старое попадётся
            out[str(y)] = [s.strip() for s in v.split(",") if s.strip()]
        else:
            out[str(y)] = []
    return out