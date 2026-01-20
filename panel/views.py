from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Prefetch
from django.utils.crypto import get_random_string
from api.models import Curso, Enrol, Horario
from .models import CursoFile, MaterialDownload, MaterialReceipt, CursoPhysicalConfig, AttendanceSession, CourseTask, TaskSubmission, PublicShareLink
from django.contrib.auth import get_user_model
import random
from django.db import models
from .decorators import require_profile_complete
from .views_attendance import _current_slot
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from django.db.models import F

try:
    from api.models import UserProfile
except ImportError:
    UserProfile = None

User = get_user_model()


TEACHER_MODULES = [
    {"slug": "info",       "label": "Información"},
    {"slug": "materiales", "label": "Materiales"},
    {"slug": "tareas", "label": "Tareas"}, 
    {"slug": "calendario", "label": "Calendario"},
    {"slug": "alumnos",    "label": "Alumnos"},
    {"slug": "ia",         "label": "IA"},
    {"slug": "chat",       "label": "Chat"},
]

STUDENT_MODULES = [
    {"slug": "info",       "label": "Información"},
    {"slug": "materiales", "label": "Materiales"},
    {"slug": "tareas", "label": "Tareas"}, 
    {"slug": "calendario", "label": "Calendario"},
    {"slug": "chat",       "label": "Chat"},
]

PHYSICAL_ITEMS = [
    {"key": "notebook", "label": "Cuaderno"},
    {"key": "pen", "label": "Bolígrafo"},
    {"key": "printed_docs", "label": "Documentación impresa"},
    {"key": "usb", "label": "Memoria USB"},
]


@login_required
def alumnos_status(request, codigo: str):
    curso = get_object_or_404(Curso, codigo=codigo)

    is_teacher = Enrol.objects.filter(user=request.user, codigo=curso.codigo, role="teacher").exists()
    if not is_teacher:
        return JsonResponse({"message": "Docente requerido"}, status=403)

    # ✅ реальный список физ. предметов из конфигурации курса
    cfg = CursoPhysicalConfig.objects.filter(curso=curso).first()
    physical_keys = (cfg.enabled_keys if cfg else []) or []

    # какие файлы видны ученикам
    visible_files_qs = CursoFile.objects.filter(curso=curso).filter(
        Q(tipo=CursoFile.TIPO_ALUMNOS) |
        (Q(share_alumnos=True) & Q(tipo__in=[CursoFile.TIPO_DOCENTES, CursoFile.TIPO_PRIVADO]))
    ).only("id", "title", "file", "module_key", "ext", "size")

    visible_ids = list(visible_files_qs.values_list("id", flat=True))
    total_visible = len(visible_ids)

    # ----- агрегаты (счетчики) -----
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

    # ----- детали для tooltip -----
    # downloads: alumno -> [file_id,...]
    dl_rows = (
        MaterialDownload.objects
        .filter(file_id__in=visible_ids)
        .values("alumno_id", "file_id")
    )

    file_map = {f.id: (f.title or f.filename) for f in visible_files_qs}

    dl_detail = {}
    for row in dl_rows:
        aid = row["alumno_id"]
        fid = row["file_id"]
        dl_detail.setdefault(aid, []).append(file_map.get(fid, f"#{fid}"))

    # receipts: alumno -> [item_label,...]
    rc_rows = (
        MaterialReceipt.objects
        .filter(curso=curso, item_key__in=physical_keys)
        .values("alumno_id", "item_label", "item_key")
    )
    # fallback label по ключу
    label_by_key = {it["key"]: it["label"] for it in PHYSICAL_ITEMS}
    rc_detail = {}
    for row in rc_rows:
        aid = row["alumno_id"]
        label = (row.get("item_label") or "").strip() or label_by_key.get(row["item_key"], row["item_key"])
        rc_detail.setdefault(aid, []).append(label)

    # все alumno_id, у кого есть хоть что-то
    all_ids = set(dl_counts.keys()) | set(rc_counts.keys()) | set(dl_detail.keys()) | set(rc_detail.keys())
    slot = _current_slot(curso)
    presence = {}

    if slot:
        day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # берём ВСЕ сессии этого слота за сегодня
        qs = (AttendanceSession.objects
              .filter(curso_codigo=curso.codigo, horario_id=slot.id, started_at__gte=day_start)
              .exclude(status=AttendanceSession.STATUS_ENDED)
              # ключевое: сначала самые “живые”
              .order_by("-last_heartbeat_at", "-last_seen_at", "-started_at", "-id")
              .values("id","user_id","status","active_sec","active_confirmed_sec",
                      "started_at","confirmed_at","last_heartbeat_at"))

        for r in qs:
            uid = str(r["user_id"])
            if uid in presence:
                continue  # уже взяли самую свежую для этого user

            presence[uid] = {
                "id": r["id"],
                "status": r["status"],
                "active_sec": int(r["active_sec"] or 0),
                "confirmed": bool(r["confirmed_at"]),
                "last": r["last_heartbeat_at"].isoformat() if r["last_heartbeat_at"] else None,
                "started": r["started_at"].isoformat() if r["started_at"] else None,
            }



    return JsonResponse({
        "total_files": total_visible,
        "total_phys": len(physical_keys),
        "items": {
            str(aid): {
                "d": int(dl_counts.get(aid, 0)),
                "r": int(rc_counts.get(aid, 0)),
                "dl": dl_detail.get(aid, []),   # ✅ названия скачанных файлов
                "rc": rc_detail.get(aid, []),   # ✅ названия подтверждённых предметов
            }
            for aid in all_ids
        },
        "slot": {"id": slot.id, "dia": slot.dia.isoformat(), "desde": slot.hora_inicio.strftime("%H:%M"), "hasta": slot.hora_fin.strftime("%H:%M")} if slot else None,
        "presence": presence
       
    })


@login_required
@require_profile_complete
def course_panel(request, codigo):
    curso = get_object_or_404(Curso, codigo=codigo)
    user = request.user
    students = []
    teachers = []

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

        # --- форматированный размер файла ---
        def _fmt_size(num):
            try:
                n = float(num or 0)
            except (TypeError, ValueError):
                n = 0.0
            for unit in ("B", "KB", "MB", "GB", "TB"):
                if n < 1024.0 or unit == "TB":
                    if unit == "B":
                        return f"{int(n)} B"
                    return f"{n:.1f} {unit}"
                n /= 1024.0
            return f"{n} B"

        # ===== Physical config (teacher chooses what exists) =====
        cfg, _ = CursoPhysicalConfig.objects.get_or_create(curso=curso)
        physical_enabled_keys = list(cfg.enabled_keys or [])
        physical_items_enabled = [it for it in PHYSICAL_ITEMS if it["key"] in physical_enabled_keys]

        context.update({
            "physical_items": PHYSICAL_ITEMS,                 # для teacher формы
            "physical_enabled_keys": physical_enabled_keys,   # для teacher формы
            "physical_items_enabled": physical_items_enabled, # для student блока
        })

        # ===== Teacher: save physical config =====
        if request.method == "POST" and is_teacher and request.POST.get("action") == "physical_config_save":
            enabled = []
            # важно: сохраняем от PHYSICAL_ITEMS (а не enabled), иначе нельзя включить новые
            for it in PHYSICAL_ITEMS:
                k = it["key"]
                if request.POST.get(f"phys_{k}") == "on":
                    enabled.append(k)
            cfg.enabled_keys = enabled
            cfg.save(update_fields=["enabled_keys", "updated_at"])
            return redirect(f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}")

        # ===== Student: receipt save (only enabled items) =====
        if request.method == "POST" and (not is_teacher) and request.POST.get("action") == "receipt_save":
            existing = set(
                MaterialReceipt.objects.filter(curso=curso, alumno=user)
                .values_list("item_key", flat=True)
            )

            for it in physical_items_enabled:
                key = it["key"]
                if key in existing:
                    continue
                if request.POST.get(f"receipt_{key}") == "on":
                    MaterialReceipt.objects.create(
                        curso=curso,
                        alumno=user,
                        item_key=key,
                        item_label=it["label"],
                    )

            return redirect(f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}")

        # ===== “Así lo ven los alumnos” (teacher preview) =====
        if is_teacher:
            # ✅ ВАЖНО: preview всегда без фильтра по модулю
            student_visible_qs = CursoFile.objects.filter(curso=curso).filter(
                Q(tipo=CursoFile.TIPO_ALUMNOS) |
                (Q(share_alumnos=True) & Q(tipo__in=[CursoFile.TIPO_DOCENTES, CursoFile.TIPO_PRIVADO]))
            )

            student_visible_files = list(student_visible_qs.order_by("-created_at")[:60])
            for f in student_visible_files:
                f.fmt_size = _fmt_size(getattr(f, "size", 0))

            context["student_visible_files"] = student_visible_files


        # ===== base queryset for this audience =====
        files_qs = CursoFile.objects.filter(curso=curso)

        if is_teacher:
            if audience == "alumnos":
                files_qs = files_qs.filter(tipo=CursoFile.TIPO_ALUMNOS)
            elif audience == "docentes":
                files_qs = files_qs.filter(tipo=CursoFile.TIPO_DOCENTES)
            elif audience == "mis":
                files_qs = files_qs.filter(tipo=CursoFile.TIPO_PRIVADO, uploaded_by=user)
        else:
            files_qs = files_qs.filter(
                Q(tipo=CursoFile.TIPO_ALUMNOS) |
                Q(tipo__in=[CursoFile.TIPO_DOCENTES, CursoFile.TIPO_PRIVADO], share_alumnos=True)
            )

        # --- teacher POST ops (upload/delete/share/copy) ---
        if request.method == "POST" and is_teacher:
            # upload
            if "upload" in request.POST:
                tipo = request.POST.get("tipo") or CursoFile.TIPO_ALUMNOS
                if tipo not in {t for t, _ in CursoFile.TIPO_CHOICES}:
                    tipo = CursoFile.TIPO_ALUMNOS

                created = 0
                for field_name, f in request.FILES.items():
                    if not field_name.startswith("file_"):
                        continue

                    suffix = field_name.split("_", 1)[1]
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
                        ext=(f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""),
                    )
                    obj.save()
                    created += 1

                return redirect(f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}")

            # delete
            if "delete_id" in request.POST:
                fid = request.POST.get("delete_id")
                cf = CursoFile.objects.filter(pk=fid, curso=curso).first()
                if cf:
                    file_name = (cf.file.name or "").strip()

                    # 1) удаляем запись
                    cf.delete()

                    # 2) удаляем физический файл ТОЛЬКО если больше нет ссылок
                    if file_name and not CursoFile.objects.filter(file=file_name).exists():
                        try:
                            cf.file.storage.delete(file_name)
                        except Exception:
                            pass

                return redirect(f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}")

            # share/unshare
            if "share_id" in request.POST:
                fid = request.POST.get("share_id")
                cf = CursoFile.objects.filter(pk=fid, curso=curso).first()
                if cf:
                    cf.share_alumnos = not cf.share_alumnos
                    cf.save(update_fields=["share_alumnos"])
                return redirect(f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}")

            # copy to privados
            if "copy_id" in request.POST:
                fid = request.POST.get("copy_id")
                src = CursoFile.objects.filter(pk=fid, curso=curso).first()
                if src:
                    new = CursoFile(
                        curso=curso,
                        uploaded_by=user,
                        tipo=CursoFile.TIPO_PRIVADO,
                        module_key=src.module_key,
                        title=src.title,
                        file=src.file,
                        size=src.size,
                        ext=src.ext,
                        share_alumnos=False,
                    )
                    new.save()
                return redirect(f"{request.path}?tab=materiales&aud={audience}&mod={selected_mod}")

        # ===== counts for filters BEFORE module filter =====
        from collections import Counter
        files_for_counts = list(files_qs)
        counts_by_mod = Counter((f.module_key or "").strip() for f in files_for_counts)

        total_files = len(files_for_counts)
        none_count = counts_by_mod.get("", 0)

        # ===== mod_groups MF → UF =====
        mod_groups = []
        for mod in tmp:
            if mod.get("kind") != "MF":
                continue
            mf_name = (mod.get("name") or "").strip()
            if not mf_name:
                continue

            items = [{"name": mf_name, "count": int(counts_by_mod.get(mf_name, 0))}]
            for c_idx in (mod.get("children") or []):
                uf_name = (tmp[c_idx].get("name") or "").strip()
                if not uf_name:
                    continue
                items.append({"name": uf_name, "count": int(counts_by_mod.get(uf_name, 0))})

            mod_groups.append({"mf": mf_name, "items": items, "total": sum(x["count"] for x in items)})

        # ===== apply module filter to actual list =====
        if selected_mod == "none":
            files_qs = files_qs.filter(module_key="")
        elif selected_mod:
            files_qs = files_qs.filter(module_key=selected_mod)

        files = list(files_qs)

        # downloaded marker for students
        if not is_teacher:
            downloaded_ids = set(
                MaterialDownload.objects.filter(alumno=user, file__in=files)
                .values_list("file_id", flat=True)
            )
            for f in files:
                f.is_downloaded = (f.id in downloaded_ids)

        # sorting by module order (from INFO list)
        mod_order = {(m["name"] or "").strip(): idx for idx, m in enumerate(mods, start=1)}

        def _file_sort_key(f):
            key = (f.module_key or "").strip()
            order = 0 if not key else mod_order.get(key, 9999)
            title = (f.title or getattr(f, "filename", "") or "").lower()
            return (order, key.lower(), title)

        files.sort(key=_file_sort_key)

        # fmt_size
        for f in files:
            f.fmt_size = _fmt_size(getattr(f, "size", 0))

        mods_with_counts = []
        for m in mods:
            name = (m["name"] or "").strip()
            if name:
                mods_with_counts.append({"name": name, "count": int(counts_by_mod.get(name, 0))})

        context.update({
            "files": files,
            "audience": audience,
            "selected_mod": selected_mod,
            "total_files": total_files,
            "none_count": none_count,
            "mods_with_counts": mods_with_counts,
            "mod_groups": mod_groups,
        })

        # ===== Receipts context for student =====
        if not is_teacher:
            qs = MaterialReceipt.objects.filter(curso=curso, alumno=user)
            receipt_keys = set(qs.values_list("item_key", flat=True))
            receipt_locked_keys = set(receipt_keys)
            keys_all = {it["key"] for it in physical_items_enabled}

            context.update({
                "receipt_keys": receipt_keys,
                "receipt_locked_keys": receipt_locked_keys,
                "receipt_all_done": (len(keys_all) > 0 and receipt_keys.issuperset(keys_all)),
            })

    # ───────────── ВКЛАДКА "TAREAS" ─────────────
    elif active_tab == "tareas":

        def _fmt_size(num):
            try:
                n = float(num or 0)
            except (TypeError, ValueError):
                n = 0.0
            for unit in ("B", "KB", "MB", "GB", "TB"):
                if n < 1024.0 or unit == "TB":
                    if unit == "B":
                        return f"{int(n)} B"
                    return f"{n:.1f} {unit}"
                n /= 1024.0
            return f"{n} B"

        # ── TEACHER: создать задачу
        if request.method == "POST" and is_teacher and request.POST.get("action") == "task_create":
            title = (request.POST.get("title") or "").strip()
            description = (request.POST.get("description") or "").strip()
            f = request.FILES.get("task_file")

            if title:
                t = CourseTask.objects.create(
                    curso=curso,
                    created_by=user,
                    title=title,
                    description=description,
                    is_published=True,
                    is_closed=False,
                )
                if f:
                    t.file = f
                    t.file_name = f.name
                    t.file_size = f.size
                    t.ext = (f.name.rsplit(".", 1)[-1].lower() if "." in f.name else "")
                    t.save(update_fields=["file", "file_name", "file_size", "ext"])

            return redirect(f"{request.path}?tab=tareas")

        # ── TEACHER: закрыть/открыть задачу
        if request.method == "POST" and is_teacher and request.POST.get("action") == "task_toggle_close":
            task_id = request.POST.get("task_id")
            t = CourseTask.objects.filter(pk=task_id, curso=curso).first()
            if t:
                t.is_closed = not bool(t.is_closed)
                t.save(update_fields=["is_closed"])
            return redirect(f"{request.path}?tab=tareas")
            
        # ── TEACHER: удалить задачу целиком
        if request.method == "POST" and is_teacher and request.POST.get("action") == "task_delete":
            task_id = request.POST.get("task_id")
            t = CourseTask.objects.filter(pk=task_id, curso=curso).first()
            if t:
                # удаляем файл задания
                if t.file:
                    t.file.delete(save=False)

                # удаляем файлы сдач + записи
                subs = TaskSubmission.objects.filter(task=t)
                for s in subs:
                    if s.file:
                        s.file.delete(save=False)
                subs.delete()

                t.delete()

            return redirect(f"{request.path}?tab=tareas")


        # ── STUDENT: отправить работу (ТОЛЬКО 1 РАЗ)
        if request.method == "POST" and (not is_teacher) and request.POST.get("action") == "task_submit":
            task_id = request.POST.get("task_id")
            f = request.FILES.get("answer_file")
            comment = (request.POST.get("comment") or "").strip()

            task = CourseTask.objects.filter(
                pk=task_id, curso=curso, is_published=True
            ).first()

            if task and (not task.is_closed) and f:
                # ✅ 1 сдача на задачу
                exists = TaskSubmission.objects.filter(task=task, alumno=user).exists()
                if not exists:
                    TaskSubmission.objects.create(
                        task=task,
                        alumno=user,
                        file=f,
                        file_name=f.name,
                        file_size=f.size,
                        ext=(f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""),
                        comment=comment,
                        status=TaskSubmission.STATUS_SUBMITTED,
                        submitted_at=timezone.now(),
                    )

            return redirect(f"{request.path}?tab=tareas")

        # ── TEACHER: поставить оценку (ТОЛЬКО 1 РАЗ, потом блок)
        if request.method == "POST" and is_teacher and request.POST.get("action") == "task_grade":
            sub_id = request.POST.get("sub_id")
            grade_raw = (request.POST.get("grade") or "").replace(",", ".").strip()
            feedback = (request.POST.get("teacher_feedback") or "").strip()

            sub = TaskSubmission.objects.select_related("task").filter(
                pk=sub_id, task__curso=curso
            ).first()

            if sub and sub.status != TaskSubmission.STATUS_GRADED:  # ✅ не даём менять после оценки
                sub.teacher_feedback = feedback
                sub.graded_by = user
                sub.graded_at = timezone.now()
                sub.status = TaskSubmission.STATUS_GRADED

                try:
                    sub.grade = float(grade_raw) if grade_raw else None
                except ValueError:
                    sub.grade = None

                sub.save()

            return redirect(f"{request.path}?tab=tareas")

        # ── queries + контекст
        if is_teacher:
            tasks = list(
                CourseTask.objects.filter(curso=curso)
                .order_by("-created_at")
                .prefetch_related(
                    Prefetch(
                        "submissions",
                        queryset=TaskSubmission.objects.select_related("alumno").order_by(
                            "status",
                            "-submitted_at"
                        )
                    )
                )
            )

            for t in tasks:
                t.fmt_size = _fmt_size(getattr(t, "file_size", 0))
                for s in t.submissions.all():
                    s.fmt_size = _fmt_size(getattr(s, "file_size", 0))

            context["tasks"] = tasks

        else:
            # ✅ STUDENT видит опубликованные задачи
            tasks = list(
                CourseTask.objects.filter(curso=curso, is_published=True)
                .order_by("-created_at")
            )

            # ✅ его сдачи (нужно для t.my_sub в шаблоне)
            my_subs = {
                s.task_id: s
                for s in TaskSubmission.objects.filter(alumno=user, task__in=tasks)
                .select_related("task")
                .order_by("-submitted_at")
            }

            for t in tasks:
                t.fmt_size = _fmt_size(getattr(t, "file_size", 0))
                t.my_sub = my_subs.get(t.id)
                if t.my_sub:
                    t.my_sub.fmt_size = _fmt_size(getattr(t.my_sub, "file_size", 0))

            context["tasks"] = tasks


    # ───────────── ВКЛАДКА "CALENDARIO" ─────────────
    elif active_tab == "calendario":
        horarios = (
            Horario.objects
            .filter(curso=curso)
            .order_by("dia", "hora_inicio")
        )

        cfg = CursoPhysicalConfig.objects.filter(curso=curso).first()
        PHYSICAL_KEYS = (cfg.enabled_keys if cfg else []) or []


        # какие файлы видимы ученикам в этом курсе
        visible_files_qs = CursoFile.objects.filter(
            curso=curso
        ).filter(
            models.Q(tipo=CursoFile.TIPO_ALUMNOS) |
            (models.Q(share_alumnos=True) & models.Q(tipo__in=[CursoFile.TIPO_DOCENTES, CursoFile.TIPO_PRIVADO]))
        )
        visible_file_ids = list(visible_files_qs.values_list("id", flat=True))
        total_visible = len(visible_file_ids)

        # скачивания: сколько файлов скачал каждый alumno (уникально по file+alumno)
        dl_map = dict(
            MaterialDownload.objects.filter(file_id__in=visible_file_ids)
            .values("alumno_id")
            .annotate(c=Count("id"))
            .values_list("alumno_id", "c")
        )

        # физматериалы: сколько галочек из 3 поставил
        rc_map = dict(
            MaterialReceipt.objects.filter(curso=curso, item_key__in=PHYSICAL_KEYS)
            .values("alumno_id")
            .annotate(c=Count("id"))
            .values_list("alumno_id", "c")
        )

        # теперь добавляем в students
        for s in students:
            s.total_files = total_visible
            s.downloaded_files = int(dl_map.get(s.id, 0))
            s.receipts_done = (int(rc_map.get(s.id, 0)))




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

            cfg = CursoPhysicalConfig.objects.filter(curso=curso).first()
            PHYSICAL_KEYS = (cfg.enabled_keys if cfg else []) or []
            visible_files_qs = CursoFile.objects.filter(curso=curso).filter(
                Q(tipo=CursoFile.TIPO_ALUMNOS) |
                (Q(share_alumnos=True) & Q(tipo__in=[CursoFile.TIPO_DOCENTES, CursoFile.TIPO_PRIVADO]))
            )
            visible_ids = list(visible_files_qs.values_list("id", flat=True))
            total_visible = len(visible_ids)

            dl_map = dict(
                MaterialDownload.objects.filter(file_id__in=visible_ids)
                .values("alumno_id").annotate(c=Count("id"))
                .values_list("alumno_id", "c")
            )

            rc_map = dict(
                MaterialReceipt.objects.filter(curso=curso, item_key__in=PHYSICAL_KEYS)
                .values("alumno_id").annotate(c=Count("id"))
                .values_list("alumno_id", "c")
            )

            for s in students:
                sid = s["id"]
                s["total_files"] = total_visible
                s["downloaded_files"] = int(dl_map.get(sid, 0))
                s["receipts_count"] = int(rc_map.get(sid, 0))


    return render(request, "panel/course_panel.html", context)

@login_required
@require_profile_complete
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
        codigo = (cursos[0].codigo or "").strip()
        return redirect("panel:course", codigo=codigo)


    # иначе показываем список курсов
    return render(request, "panel/alumno_home.html", {
        "cursos": cursos,
        "is_teacher": is_teacher,
    })
    
from django.http import FileResponse, Http404
def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def user_can_access_course(user, curso: Curso) -> bool:
    # teacher
    if Enrol.objects.filter(user=user, codigo=curso.codigo, role="teacher").exists():
        return True
    # student
    if Enrol.objects.filter(user=user, codigo=curso.codigo).exclude(role="teacher").exists():
        return True
    return False

@login_required
def material_download(request, file_id: int):
    f = CursoFile.objects.select_related("curso", "uploaded_by").filter(id=file_id).first()
    if not f:
        raise Http404

    curso = f.curso

    # доступ к курсу
    if not user_can_access_course(request.user, curso):
        raise Http404

    # определяем роль (как у тебя в course_panel)
    is_teacher = Enrol.objects.filter(user=request.user, codigo=curso.codigo, role="teacher").exists()

    # доступ к самому файлу (важно для alumnos)
    if not f.can_see(request.user, is_teacher=is_teacher):
        raise Http404

    # логируем ТОЛЬКО для учеников (для отчётности)
    if not is_teacher:
        MaterialDownload.objects.get_or_create(
            file=f,
            alumno=request.user,
            defaults={
                "ip": get_client_ip(request),
                "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:255],
            },
        )

    return FileResponse(f.file.open("rb"), as_attachment=True, filename=f.filename or None)
    
@login_required
def task_download(request, codigo: str, task_id: int):
    curso = get_object_or_404(Curso, codigo=codigo)
    if not user_can_access_course(request.user, curso):
        raise Http404

    task = CourseTask.objects.filter(pk=task_id, curso=curso, is_published=True).first()
    if not task or not task.file:
        raise Http404

    return FileResponse(task.file.open("rb"), as_attachment=True, filename=task.filename or None)


@login_required
def submission_download(request, codigo: str, task_id: int, sub_id: int):
    curso = get_object_or_404(Curso, codigo=codigo)
    if not user_can_access_course(request.user, curso):
        raise Http404

    is_teacher = Enrol.objects.filter(user=request.user, codigo=curso.codigo, role="teacher").exists()

    sub = TaskSubmission.objects.select_related("task").filter(pk=sub_id, task_id=task_id, task__curso=curso).first()
    if not sub or not sub.file:
        raise Http404

    # ученик — только свой файл
    if (not is_teacher) and (sub.alumno_id != request.user.id):
        raise Http404

    return FileResponse(sub.file.open("rb"), as_attachment=True, filename=sub.filename or None)

# api/views_me.py (примерно)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.models import UserProfile

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def me_profile(request):
    p, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "GET":
        return Response({
            "profile": {
                "first_name": p.first_name,
                "last_name1": p.last_name1,
                "last_name2": p.last_name2,
                "display_name": p.display_name,
                "bio": p.bio,
                "is_teacher": p.is_teacher,
                "is_complete": p.is_complete(),
            }
        })

    data = request.data or {}
    p.first_name   = (data.get("first_name") or "").strip()
    p.last_name1   = (data.get("last_name1") or "").strip()
    p.last_name2   = (data.get("last_name2") or "").strip()
    p.display_name = (data.get("display_name") or "").strip()
    p.bio          = (data.get("bio") or "").strip()

    # ✅ если display пустой — сгенерим из имени/фамилий
    if not p.display_name:
        gen = p.build_display_name()
        if gen:
            p.display_name = gen

    p.save()
    return Response({"ok": True, "profile": {
        "first_name": p.first_name,
        "last_name1": p.last_name1,
        "last_name2": p.last_name2,
        "display_name": p.display_name,
        "bio": p.bio,
        "is_complete": p.is_complete(),
    }})


@csrf_exempt
@require_http_methods(["POST"])
def material_share_link_create(request, file_id: int):
    """
    POST /panel/materiales/<file_id>/share-link
    -> {"ok": true, "url": "...", "expires_at": "..."}
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"ok": False, "error": "auth_required"}, status=401)

    # твоя логика: teacher/admin
    is_teacher = getattr(user, "is_staff", False) or getattr(user, "is_teacher", False)
    if not is_teacher:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    cf = CursoFile.objects.select_related("curso").filter(pk=file_id).first()
    if not cf:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)

    # ⚠️ Политика: какие файлы можно отдавать публично?
    # Я бы разрешил только то, что видимо ученикам:
    # - alumnos
    # - или share_alumnos=True (docentes/privado)
    allowed_public = (cf.tipo == "alumnos") or (cf.share_alumnos and cf.tipo in ("docentes", "privado"))
    if not allowed_public:
        return JsonResponse({"ok": False, "error": "not_publicable"}, status=400)

    # срок жизни (например, 14 дней). Можно сделать настройкой.
    ttl_days = 14
    expires_at = timezone.now() + timedelta(days=ttl_days)

    # создаём новый токен (или можно "переиспользовать" активный)
    link = PublicShareLink.objects.create(
        token=PublicShareLink.new_token(),
        file=cf,
        created_by=user,
        expires_at=expires_at,
        is_active=True,
    )

    # абсолютная ссылка
    url = request.build_absolute_uri(f"/alumno/s/{link.token}/")


    return JsonResponse({
        "ok": True,
        "url": url,
        "expires_at": link.expires_at.isoformat() if link.expires_at else None
    })

from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

@require_GET
def public_share_download(request, token: str):
    """
    GET /s/<token>
    -> отдаёт файл как download, без логина
    """
    link = PublicShareLink.objects.select_related("file").filter(token=token).first()
    if not link or not link.is_valid():
        raise Http404()

    cf = link.file

    # Доп. защита: если после создания ссылки файл стал "не видим ученикам" — блокируем.
    allowed_public = (cf.tipo == "alumnos") or (cf.share_alumnos and cf.tipo in ("docentes", "privado"))
    if not allowed_public:
        raise Http404()

    # Здесь можно логировать скачивания анонимных (по желанию)
    # MaterialDownload.objects.create(... user=None, ...)

    # Отдаём файл
    f = cf.file
    if not f:
        raise Http404()

    resp = HttpResponse(f.open("rb").read(), content_type="application/octet-stream")
    filename = cf.filename or "material"
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp
