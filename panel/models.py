# panel/models.py
from django.db import models
from django.conf import settings
from api.models import Curso   # тот самый Curso, что у тебя уже есть


User = settings.AUTH_USER_MODEL

class TempAccess(models.Model):
    """
    Временный аккаунт типа Alumno01 -> '42' для курса.
    Привязан к конкретному преподавателю (teacher) и курсу.
    """
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="temp_accesses",
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name="temp_accesses",
    )
    temp_name = models.CharField(max_length=32)   # Alumno01
    key = models.CharField(max_length=8)          # '00'..'99' (но можно и больше)
    used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("teacher", "curso", "temp_name")

    def __str__(self):
        return f"{self.curso.codigo} · {self.teacher_id} · {self.temp_name}={self.key}"


def curso_file_upload_path(instance, filename):
    """
    Файлы физически будут в:
    BASE_DIR / files / curso_files / <CODIGO> / filename
    """
    codigo = (instance.curso.codigo or "curso").replace("/", "_")
    return f"curso_files/{codigo}/{filename}"


class CursoFile(models.Model):
    TIPO_ALUMNOS = "alumnos"
    TIPO_DOCENTES = "docentes"
    TIPO_PRIVADO = "privado"

    TIPO_CHOICES = [
        (TIPO_ALUMNOS, "Para alumnos"),
        (TIPO_DOCENTES, "Docentes"),
        (TIPO_PRIVADO, "Privados (míos)"),
    ]

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="files")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="curso_files",
    )
    folder_path = models.CharField(max_length=500, blank=True, default="", db_index=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default=TIPO_ALUMNOS)

    # модуль (MF/UF или slug), как в старом фронте: module_key
    module_key = models.CharField(max_length=255, blank=True)

    title = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to=curso_file_upload_path)

    size = models.PositiveIntegerField(default=0)
    ext = models.CharField(max_length=16, blank=True)

    # видно ли этот ресурс ученикам, если он из зоны DOCENTES/PRIVADO
    share_alumnos = models.BooleanField(default=False)

    locked = models.BooleanField(default=False)  # если пригодится «нельзя удалить»
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.curso.codigo} · {self.title or self.filename}"

    @property
    def display_name(self):
        t = (self.title or "").strip()
        return t or self.filename or f"Archivo #{self.id}"

    @property
    def filename(self):
        return self.file.name.rsplit("/", 1)[-1]

    def can_see(self, user, is_teacher: bool):
        """Проверка доступа на просмотр."""
        if is_teacher:
            # преподаватель видит всё по курсу
            return True

        # ученик
        if self.tipo == self.TIPO_ALUMNOS:
            return True
        if self.share_alumnos and self.tipo in (self.TIPO_DOCENTES, self.TIPO_PRIVADO):
            return True
        return False

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

# panel/models.py
class CursoFolder(models.Model):
    curso = models.ForeignKey("api.Curso", on_delete=models.CASCADE, related_name="folders")
    path = models.CharField(max_length=500, db_index=True)   # уникальный путь внутри курса
    title = models.CharField(max_length=200, blank=True, default="")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    is_locked = models.BooleanField(default=False)   # модули = True
    is_deleted = models.BooleanField(default=False)  # мягкое удаление (удобно)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("curso", "path")


class MaterialDownload(models.Model):
    file = models.ForeignKey(
        CursoFile,
        on_delete=models.CASCADE,
        related_name="downloads"
    )
    alumno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="material_downloads"
    )

    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["file", "alumno"]),
            models.Index(fields=["alumno", "-downloaded_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["file", "alumno"],
                name="uniq_file_download_per_alumno"
            ),
        ]


class MaterialReceipt(models.Model):
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name="receipts"
    )
    alumno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="material_receipts"
    )

    item_key = models.CharField(max_length=50)
    item_label = models.CharField(max_length=120, blank=True, default="")

    received = models.BooleanField(default=True)
    received_at = models.DateTimeField(auto_now_add=True)

    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["curso", "alumno", "item_key"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["curso", "alumno", "item_key"],
                name="uniq_receipt_item_per_course"
            ),
        ]
        
class CursoPhysicalConfig(models.Model):
    curso = models.OneToOneField(Curso, on_delete=models.CASCADE, related_name="physical_cfg")
    enabled_keys = models.JSONField(default=list, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.curso.codigo} · physical_cfg"

from django.utils import timezone

def task_upload_path(instance, filename):
    codigo = (instance.curso.codigo or "curso").replace("/", "_")
    return f"curso_tasks/{codigo}/{filename}"

def submission_upload_path(instance, filename):
    codigo = (instance.task.curso.codigo or "curso").replace("/", "_")
    return f"task_submissions/{codigo}/task{instance.task_id}/user{instance.alumno_id}/{filename}"


class CourseTask(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="tasks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_tasks")

    # ✅ модуль курса (MF/UF/slug) — как в CursoFile
    module_key = models.CharField(max_length=255, blank=True, db_index=True)
    module_label = models.CharField(max_length=190, blank=True, default="")  # опционально

    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    is_final_exam = models.BooleanField(default=False, db_index=True)
    convocatoria = models.PositiveSmallIntegerField(
        null=True, blank=True, db_index=True,
        choices=[(1, "1ª"), (2, "2ª")]
    )
    file = models.FileField(upload_to=task_upload_path, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, default="")
    file_size = models.BigIntegerField(default=0)
    ext = models.CharField(max_length=16, blank=True, default="")

    due_at = models.DateTimeField(blank=True, null=True)
    is_published = models.BooleanField(default=True)
    
    is_closed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def filename(self):
        return self.file_name or (self.file.name.rsplit("/", 1)[-1] if self.file else "")


class TaskSubmission(models.Model):
    STATUS_SUBMITTED = "submitted"
    STATUS_GRADED = "graded"
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Entregado"),
        (STATUS_GRADED, "Calificado"),
    ]

    task = models.ForeignKey(CourseTask, on_delete=models.CASCADE, related_name="submissions")
    alumno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_submissions")

    file = models.FileField(upload_to=submission_upload_path, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, default="")
    file_size = models.BigIntegerField(default=0)
    ext = models.CharField(max_length=16, blank=True, default="")

    comment = models.TextField(blank=True, default="")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    submitted_at = models.DateTimeField(default=timezone.now)

    grade = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # 0..10 например
    teacher_feedback = models.TextField(blank=True, default="")
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="graded_task_submissions")
    graded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "alumno"], name="uniq_submission_per_task_alumno"),
        ]
        ordering = ["-submitted_at"]

    @property
    def filename(self):
        return self.file_name or (self.file.name.rsplit("/", 1)[-1] if self.file else "")

import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta

class PublicShareLink(models.Model):
    token = models.CharField(max_length=64, unique=True, db_index=True)
    file = models.ForeignKey("panel.CursoFile", on_delete=models.CASCADE, related_name="share_links")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_share_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def new_token():
        return secrets.token_urlsafe(16)

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() >= self.expires_at:
            return False
        return True


# api/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

class AttendanceSession(models.Model):
    STATUS_OFFSITE   = "OFFSITE"
    STATUS_PENDING   = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_REJECTED  = "REJECTED"
    STATUS_ENDED     = "ENDED"

    STATUS_CHOICES = [
        (STATUS_OFFSITE, "Offsite"),
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_ENDED, "Ended"),
    ]

    curso_codigo = models.CharField(max_length=32, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_sessions")

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    # кто подтвердил/отклонил
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_confirmed")
    decided_at = models.DateTimeField(null=True, blank=True)

    # время/живость
    started_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    horario = models.ForeignKey("api.Horario", null=True, blank=True, on_delete=models.SET_NULL, related_name="attendance_sessions")

    lesson_date = models.DateField(db_index=True, null=True, blank=True)
    lesson_start = models.TimeField(null=True, blank=True)
    lesson_end = models.TimeField(null=True, blank=True)

    active_sec = models.PositiveIntegerField(default=0)
    active_confirmed_sec = models.PositiveIntegerField(default=0)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    # техданные
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    session_id = models.CharField(max_length=64, blank=True, default="")  # можно прокинуть твой mz_sid

    class Meta:
        indexes = [
            models.Index(fields=["curso_codigo", "horario", "status"]),
            models.Index(fields=["curso_codigo", "horario", "started_at"]),
            models.Index(fields=["user", "curso_codigo", "horario"]),
        ]


    def is_alive(self, hb_sec: int = 90) -> bool:
        t = self.last_heartbeat_at or self.confirmed_at or self.started_at
        return (timezone.now() - t).total_seconds() <= hb_sec

class CursoPhysicalItem(models.Model):
    curso = models.ForeignKey("api.Curso", on_delete=models.CASCADE, related_name="physical_items")
    key = models.SlugField(max_length=60)          # "usb", "cuaderno-a4", ...
    label = models.CharField(max_length=120)       # "Memoria USB"
    is_enabled = models.BooleanField(default=True) # показывать ученику
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("curso", "key"),)
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.curso.codigo}: {self.label}"
