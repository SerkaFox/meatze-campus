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

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default=TIPO_ALUMNOS)

    # модуль (MF/UF или slug), как в старом фронте: module_key
    module_key = models.CharField(max_length=50, blank=True)

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

