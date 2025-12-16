from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.crypto import get_random_string

from api.models import Curso, Enrol, Horario
from .models import CursoFile
from django.contrib.auth import get_user_model
import random
try:
    from api.models import UserProfile
except ImportError:
    UserProfile = None

User = get_user_model()


TEACHER_MODULES = [
    {"slug": "info",       "label": "Información"},
    {"slug": "materiales", "label": "Materiales"},
    {"slug": "calendario", "label": "Calendario"},
    {"slug": "alumnos",    "label": "Alumnos"},
    {"slug": "ia",         "label": "IA"},
    {"slug": "chat",       "label": "Chat"},
]

STUDENT_MODULES = [
    {"slug": "info",       "label": "Información"},
    {"slug": "materiales", "label": "Materiales"},
    {"slug": "calendario", "label": "Calendario"},
    {"slug": "chat",       "label": "Chat"},
]


@login_required
def course_panel(request, codigo):
    curso = get_object_or_404(Curso, codigo=codigo)
    user = request.user
    is_teacher = Enrol.objects.filter(
        user=user,
        codigo=curso.codigo,
        role="teacher",
    ).exists()

    modules_cfg = TEACHER_MODULES if is_teacher else STUDENT_MODULES
    active_tab = request.GET.get("tab", "info")

    # --- варианты аудитории для вкладки "Materiales" ---
    if is_teacher:
        audience_options = [
            ("alumnos", "Para alumnos"),
            ("docentes", "Docentes"),
            ("mis", "Privados (míos)"),
        ]
    else:
        # у студента одна кнопка, просто текст красивый
        audience_options = [
            ("alumnos", "Materiales del curso"),
        ]

    # --- модули курса для вкладки INFO ---
    # --- модули курса для вкладки INFO ---
    raw_mods = curso.modules or []

    def _get_name(m):
        return (m.get("name") or m.get("nombre") or m.get("titulo") or "").strip()

    def _get_code(m):
        return (m.get("code") or m.get("codigo") or m.get("clave") or "").strip()

    def _get_direct_hours(m):
        h = m.get("hours") or m.get("horas") or 0
        try:
            return float(h)
        except (TypeError, ValueError):
            return 0.0

    def _guess_kind(m):
        """
        Пытаемся понять MF/UF по коду или первому слову.
        """
        code = _get_code(m)
        name = _get_name(m)
        token = (code or name).split()[0].upper()
        if token.startswith("MF"):
            return "MF"
        if token.startswith("UF"):
            return "UF"
        return ""

    # временная структура с привязкой UF -> MF
    tmp = []
    current_mf_idx = None
    parent_for_child = {}

    for m in raw_mods:
        if not isinstance(m, dict):
            continue

        name = _get_name(m)
        code = _get_code(m)
        kind = _guess_kind(m)
        hours_direct = _get_direct_hours(m)

        idx = len(tmp)
        tmp.append({
            "name": name,
            "code": code,
            "kind": kind,          # "MF" / "UF" / ""
            "hours_direct": hours_direct,
            "hours": hours_direct,  # финальное значение заполним ниже
            "children": [],
        })

        if kind == "MF":
            current_mf_idx = idx
        elif kind == "UF" and current_mf_idx is not None:
            tmp[current_mf_idx]["children"].append(idx)
            parent_for_child[idx] = current_mf_idx
        else:
            current_mf_idx = None

    # 1) для MF с 0 часами — суммируем их UF
    for i, mod in enumerate(tmp):
        if mod["kind"] == "MF":
            if mod["hours_direct"] > 0:
                continue
            children = mod.get("children") or []
            agg = 0.0
            for c_idx in children:
                agg += tmp[c_idx]["hours_direct"]
            mod["hours"] = agg
        else:
            mod["hours"] = mod["hours_direct"]

    # 2) считаем общую длительность, не удваивая UF
    total_hours = 0.0
    for i, mod in enumerate(tmp):
        if mod["kind"] == "MF":
            total_hours += mod["hours"]
        elif mod["kind"] == "UF":
            # добавляем только UF, которые ни к одному MF не привязаны
            if i not in parent_for_child:
                total_hours += mod["hours"]
        else:
            total_hours += mod["hours"]

    # 3) простой список для шаблона
    mods = [{"name": m["name"], "hours": m["hours"]} for m in tmp]

    # базовый контекст — один раз
    context = {
        "curso": curso,
        "mods": mods,
        "total_hours": total_hours,   # <<< добавили
        "is_teacher": is_teacher,
        "modules_cfg": modules_cfg,
        "active_tab": active_tab,
        "audience_options": audience_options,
    }
    context["IS_TEACHER"] = request.user.groups.filter(name="Docente").exists()
    context["USER_ID"] = request.user.id

    # ───────────── ВКЛАДКА "MATERIALES" ─────────────
    if active_tab == "materiales":
        audience = request.GET.get("aud", "alumnos")  # alumnos/docentes/mis
        selected_mod = request.GET.get("mod") or ""   # ""=все, "none"=без модуля

        if not is_teacher:
            audience = "alumnos"

        files_qs = CursoFile.objects.filter(curso=curso)

        if is_teacher:
            if audience == "alumnos":
                files_qs = files_qs.filter(tipo=CursoFile.TIPO_ALUMNOS)
            elif audience == "docentes":
                files_qs = files_qs.filter(tipo=CursoFile.TIPO_DOCENTES)
            elif audience == "mis":
                files_qs = files_qs.filter(
                    tipo=CursoFile.TIPO_PRIVADO,
                    uploaded_by=user,
                )
        else:
            files_qs = files_qs.filter(
                Q(tipo=CursoFile.TIPO_ALUMNOS) |
                Q(
                    tipo__in=[CursoFile.TIPO_DOCENTES, CursoFile.TIPO_PRIVADO],
                    share_alumnos=True,
                )
            )

        if selected_mod == "none":
            files_qs = files_qs.filter(module_key="")
        elif selected_mod:
            files_qs = files_qs.filter(module_key=selected_mod)

        # --- POST-операции только для преподавателя ---
        if request.method == "POST" and is_teacher:
            # upload — теперь несколько файлов: file_1, file_2, ...
            if "upload" in request.POST:
                tipo = request.POST.get("tipo") or CursoFile.TIPO_ALUMNOS
                if tipo not in {t for t, _ in CursoFile.TIPO_CHOICES}:
                    tipo = CursoFile.TIPO_ALUMNOS

                created = 0

                for field_name, f in request.FILES.items():
                    if not field_name.startswith("file_"):
                        continue

                    suffix = field_name.split("_", 1)[1]  # "1", "2", ...
                    mod_key = (request.POST.get(f"module_key_{suffix}") or "").strip()
                    title = (request.POST.get(f"title_{suffix}") or "").strip()

                    obj = CursoFile(
                        curso=curso,
                        uploaded_by=user,
                        tipo=tipo,
                        module_key=mod_key,
                        title=title or f.name,
                        file=f,
                        size=f.size,
                        ext=(
                            f.name.rsplit(".", 1)[-1].lower()
                            if "." in f.name else ""
                        ),
                    )
                    obj.save()
                    created += 1

                # на всякий случай fallback: если по каким-то причинам не было file_*
                if created == 0:
                    f = request.FILES.get("file")
                    if f:
                        mod_key = (request.POST.get("module_key") or "").strip()
                        title = (request.POST.get("title") or "").strip()
                        obj = CursoFile(
                            curso=curso,
                            uploaded_by=user,
                            tipo=tipo,
                            module_key=mod_key,
                            title=title or f.name,
                            file=f,
                            size=f.size,
                            ext=(
                                f.name.rsplit(".", 1)[-1].lower()
                                if "." in f.name else ""
                            ),
                        )
                        obj.save()

                return redirect(
                    f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}"
                )


            # delete
            if "delete_id" in request.POST:
                fid = request.POST.get("delete_id")
                try:
                    cf = CursoFile.objects.get(pk=fid, curso=curso)
                except CursoFile.DoesNotExist:
                    pass
                else:
                    cf.file.delete(save=False)
                    cf.delete()
                return redirect(
                    f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}"
                )

            # share/unshare
            if "share_id" in request.POST:
                fid = request.POST.get("share_id")
                try:
                    cf = CursoFile.objects.get(pk=fid, curso=curso)
                except CursoFile.DoesNotExist:
                    pass
                else:
                    cf.share_alumnos = not cf.share_alumnos
                    cf.save(update_fields=["share_alumnos"])
                return redirect(
                    f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}"
                )

            # копировать в privados
            if "copy_id" in request.POST:
                fid = request.POST.get("copy_id")
                try:
                    src = CursoFile.objects.get(pk=fid, curso=curso)
                except CursoFile.DoesNotExist:
                    pass
                else:
                    new = CursoFile(
                        curso=curso,
                        uploaded_by=user,
                        tipo=CursoFile.TIPO_PRIVADO,
                        module_key=src.module_key,
                        title=src.title,
                        file=src.file,  # та же физическая ссылка
                        size=src.size,
                        ext=src.ext,
                        share_alumnos=False,
                    )
                    new.save()

                return redirect(
                    f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}"
                )

        # --- сначала считаем файлы по модулям (для текущей audience) ---
        # --- сначала считаем файлы по модулям (для текущей audience) ---
        from collections import Counter

        files_for_counts = list(files_qs)
        counts_by_mod = Counter()

        for f in files_for_counts:
            key = (f.module_key or "").strip()
            counts_by_mod[key] += 1

        total_files = len(files_for_counts)
        none_count = counts_by_mod.get("", 0)

        # теперь применяем фильтр по модулю
        if selected_mod == "none":
            files_qs = files_qs.filter(module_key="")
        elif selected_mod:
            files_qs = files_qs.filter(module_key=selected_mod)

        files = list(files_qs)

        # --- сортировка по порядку модулей (как во вкладке INFO) ---
        mod_order = {(m["name"] or "").strip(): idx for idx, m in enumerate(mods, start=1)}

        def _file_sort_key(f):
            key = (f.module_key or "").strip()
            if not key:
                order = 0
            else:
                order = mod_order.get(key, 9999)
            title = (f.title or getattr(f, "filename", "") or "").lower()
            return (order, key.lower(), title)

        files.sort(key=_file_sort_key)

        # --- форматированный размер файла ---
        def _fmt_size(num):
            try:
                n = int(num or 0)
            except (TypeError, ValueError):
                n = 0
            for unit in ("B", "KB", "MB", "GB"):
                if n < 1024 or unit == "GB":
                    if unit == "B":
                        return f"{n} B"
                    return f"{n / 1024:.1f} {unit}"
                n //= 1024
            return f"{n} B"

        for f in files:
            f.fmt_size = _fmt_size(getattr(f, "size", 0))

        # список модулей с количеством файлов (для пилюль)
        mods_with_counts = []
        for m in mods:
            name = (m["name"] or "").strip()
            if not name:
                continue
            mods_with_counts.append({
                "name": name,
                "count": counts_by_mod.get(name, 0),
            })

        context.update({
            "files": files,
            "audience": audience,
            "selected_mod": selected_mod,
            "total_files": total_files,
            "none_count": none_count,
            "mods_with_counts": mods_with_counts,
        })



    # ───────────── ВКЛАДКА "CALENDARIO" ─────────────
    elif active_tab == "calendario":
        horarios = (
            Horario.objects
            .filter(curso=curso)
            .order_by("dia", "hora_inicio")
        )

        # данные для JS-календаря
        horarios_data = []
        for h in horarios:
            horarios_data.append({
                "dia": h.dia.isoformat(),                  # '2025-12-22'
                "hora_inicio": h.hora_inicio.strftime("%H:%M"),
                "hora_fin": h.hora_fin.strftime("%H:%M"),
                "aula": h.aula,
                "modulo": h.modulo,
                "tipo": h.tipo,
                "grupo": h.grupo,
            })

        context["horarios"] = horarios
        context["horarios_data"] = horarios_data
        
        # ───────────── ВКЛАДКА "ALUMNOS" ─────────────
    elif active_tab == "alumnos":
        # только преподаватель видит эту вкладку (guard стоит и в меню)
        if not is_teacher:
            context["students"] = []
        else:
            # кэш последних сгенерированных паролей в сессии
            last_passes = request.session.get("panel_last_passes", {})

            # обработка POST: reset / remove
            if request.method == "POST":
                # удалить ученика с курса
                if "remove_id" in request.POST:
                    uid = request.POST.get("remove_id")
                    try:
                        uid_int = int(uid)
                    except (TypeError, ValueError):
                        uid_int = None

                    if uid_int:
                        Enrol.objects.filter(
                            user_id=uid_int,
                            codigo=curso.codigo,
                            role="student",
                        ).delete()
                        # уберём и из кэша паролей
                        last_passes.pop(str(uid_int), None)

                    request.session["panel_last_passes"] = last_passes
                    return redirect(f"{request.path}?tab=alumnos")

                # сбросить пароль ученику
                if "reset_id" in request.POST:
                    uid = request.POST.get("reset_id")
                    try:
                        uid_int = int(uid)
                    except (TypeError, ValueError):
                        uid_int = None

                    if uid_int:
                        try:
                            u = User.objects.get(pk=uid_int)
                        except User.DoesNotExist:
                            pass
                        else:
                            # генерим новый простой пароль (можешь поменять длину/алфавит)
                            new_pwd = f"{random.randint(0, 9999):04d}"
                            u.set_password(new_pwd)
                            u.save(update_fields=["password"])
                            last_passes[str(uid_int)] = new_pwd

                    request.session["panel_last_passes"] = last_passes
                    return redirect(f"{request.path}?tab=alumnos")

            # GET: собираем список студентов
            enrols = (
                Enrol.objects
                .filter(codigo=curso.codigo, role="student")
                .select_related("user")
                .order_by("created_at")
            )

            students = []
            from django.utils import timezone

            for idx, enr in enumerate(enrols, start=1):
                u = enr.user

                # пробуем достать профиль
                profile = None
                if UserProfile is not None:
                    # сначала через related_name, если настроен (user.userprofile)
                    profile = getattr(u, "userprofile", None)
                    # запасной вариант — прямой поиск
                    if profile is None:
                        profile = UserProfile.objects.filter(user=u).first()

                if profile and getattr(profile, "display_name", ""):
                    display_name = profile.display_name.strip()
                else:
                    display_name = (
                        (u.get_full_name() or "").strip()
                        or (u.username or "") 
                        or (u.email or "")
                        or f"ID {u.pk}"
                    )

                students.append({
                    "idx": idx,
                    "id": u.pk,
                    "email": u.email,
                    "name": display_name,
                    "enrol_created_at": enr.created_at,
                    "last_pass": last_passes.get(str(u.pk)),
                })


            context.update({
                "students": students,
            })



    return render(request, "panel/course_panel.html", context)


@login_required
def alumno_home(request):
    user = request.user
    is_teacher = Enrol.objects.filter(user=user, role="teacher").exists()

    # --- курсы через Enrol ---
    if is_teacher:
        # все курсы, где он назначен как teacher
        codigos = (
            Enrol.objects
            .filter(user=user, role="teacher")
            .values_list("codigo", flat=True)
            .distinct()
        )
    else:
        # все курсы, где он ученик (любая роль, кроме teacher)
        codigos = (
            Enrol.objects
            .filter(user=user)
            .exclude(role="teacher")
            .values_list("codigo", flat=True)
            .distinct()
        )

    cursos = list(
        Curso.objects.filter(codigo__in=codigos).order_by("codigo")
    )

    # если ровно один курс — сразу кидаем в панель этого курса
    if len(cursos) == 1:
        return redirect("panel:course", codigo=cursos[0].codigo)

    # иначе показываем список курсов
    return render(request, "panel/alumno_home.html", {
        "cursos": cursos,
        "is_teacher": is_teacher,
    })
