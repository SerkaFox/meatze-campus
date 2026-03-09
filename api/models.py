from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from .chat_models import ChatMessage, ChatRead, ChatReaction
from .utils_wa import normalize_wa
User = get_user_model()

class MZSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)

    def __str__(self):
        return self.key
# ─────────── CURSOS ───────────

from django.utils import timezone

class LoginPIN(models.Model):
    email = models.EmailField(db_index=True)
    pin = models.CharField(
        max_length=6,
        db_index=True,
        default=''   # 👈 добавили дефолт
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} · {self.pin}"

from django.utils import timezone

class PendingRole(models.Model):
    ROLE_CHOICES = (
        ("unknown", "Unknown"),
        ("teacher", "Teacher"),
        ("student", "Student"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pending_roles")
    email = models.EmailField(db_index=True)

    # что запросил пользователь (или ставим unknown)
    requested_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="unknown")

    # решение админа
    decided_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="unknown")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.email} · {self.status} · req={self.requested_role} decided={self.decided_role}"


class WaContact(models.Model):
    """
    Аналог wp_meatze_subs_wa:
    wa, name, loc, active, created_at
    """
    LOC_CHOICES = [
        ("Bilbao", "Bilbao"),
        ("Barakaldo", "Barakaldo"),
    ]

    wa = models.CharField("Número WhatsApp", max_length=32, unique=True)
    name = models.CharField("Nombre", max_length=190, blank=True, default="")
    loc = models.CharField("Localidad", max_length=50, blank=True, default="", choices=LOC_CHOICES)
    active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "meatze_subs_wa"  # чтобы легко переехать с WP
        verbose_name = "WA contact"
        verbose_name_plural = "WA contacts"

    def __str__(self):
        return f"{self.name or '—'} ({self.wa})"


class WaInbox(models.Model):
    """
    Аналог wp_meatze_wa_inbox:
    входящие/исходящие WA сообщения
    """
    DIRECTION_CHOICES = [
        ("in", "In"),
        ("out", "Out"),
    ]

    wa = models.CharField(max_length=32)
    name = models.CharField(max_length=190, blank=True, default="")
    source = models.CharField(max_length=20, default="meatze")
    msg = models.TextField()
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, default="in")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "meatze_wa_inbox"
        indexes = [
            models.Index(fields=["wa"]),
            models.Index(fields=["source"]),
            models.Index(fields=["direction"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"[{self.direction}] {self.wa}: {self.msg[:50]}"



class Curso(models.Model):
    codigo = models.CharField(max_length=64, unique=True)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, default="")
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    live_is_open = models.BooleanField(default=False)
    live_opened_at = models.DateTimeField(null=True, blank=True)
    live_closed_at = models.DateTimeField(null=True, blank=True)
    live_last_signal_at = models.DateTimeField(null=True, blank=True)  # heartbeat от лог-вотчера
    # новые поля для админ-панели
    modules = models.JSONField(default=list, blank=True)
    horas_total = models.PositiveIntegerField(default=0)
    use_global_nonlective = models.BooleanField(default=True)

    # личные дни центра для этого курса:
    # {"2025":"01/01, 02/01-03/01", "2026":"..."}  (как сейчас у FIXED_NONLECTIVE)
    nonlective_years = models.JSONField(default=dict, blank=True)
    TIPO_FORMACION_CHOICES = [
        ("ocupacional", "Ocupacional"),
        ("continua", "Continua"),
    ]

    tipo_formacion = models.CharField(
        max_length=20,
        choices=TIPO_FORMACION_CHOICES,
        blank=True,
        default="",
    )


    def __str__(self):
        return f"{self.codigo} – {self.titulo}"


# ─────────── ENROLS ───────────

class Enrol(models.Model):
    ROLE_CHOICES = (
        ("teacher", "Teacher"),
        ("student", "Student"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrolments",
    )
    # ВРЕМЕННО позволяем пустое + задаём дефолт
    codigo = models.CharField(max_length=64, blank=True, default="")

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "codigo", "role")



# ─────────── HORARIOS ───────────

class Horario(models.Model):
    curso = models.ForeignKey("Curso", on_delete=models.CASCADE, related_name="horarios")
    dia = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    aula = models.CharField(max_length=100, blank=True, default="")
    modulo = models.CharField(max_length=255, blank=True, default="")

    tipo = models.CharField(
        max_length=20,
        blank=True,
        default="",   # "curso" / "practica" / "" (по умолчанию)
    )
    grupo = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    class Meta:
        ordering = ["dia", "hora_inicio"]


# ─────────── USER PROFILE ───────────
# (для модалки "Datos personales" + флаг docente)

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    first_name   = models.CharField(max_length=150, blank=True)
    last_name1   = models.CharField(max_length=150, blank=True)
    last_name2   = models.CharField(max_length=150, blank=True)
    display_name = models.CharField(max_length=190, blank=True)
    bio          = models.TextField(blank=True)
    wa = models.CharField(max_length=32, blank=True, default="", db_index=True)

    is_teacher   = models.BooleanField(default=False)

    def build_display_name(self) -> str:
        parts = [(self.first_name or "").strip(), (self.last_name1 or "").strip(), (self.last_name2 or "").strip()]
        parts = [p for p in parts if p]
        return " ".join(parts)

    def is_complete(self) -> bool:
        return bool((self.first_name or "").strip() and (self.last_name1 or "").strip())

    def save(self, *args, **kwargs):
        # ✅ если display_name пустой, но имя/апеллидо есть — генерим
        if not (self.display_name or "").strip():
            gen = self.build_display_name()
            if gen:
                self.display_name = gen
        self.wa = normalize_wa(self.wa) if (self.wa or "").strip() else ""
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.user.get_full_name() or self.user.username

from django.db import models
from django.conf import settings

class LearningEvent(models.Model):
    curso_codigo = models.CharField(max_length=32, db_index=True, blank=True, default="")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_events")

    session_id = models.CharField(max_length=64, db_index=True, blank=True, default="")  # фронт UUID
    seq = models.PositiveIntegerField(default=0)  # порядковый номер события в сессии

    event = models.CharField(max_length=50, db_index=True)  # click, view, login, open_file, quiz_start...
    object_type = models.CharField(max_length=50, blank=True, default="")
    object_id = models.CharField(max_length=64, blank=True, default="")

    page = models.CharField(max_length=200, blank=True, default="")      # /alumno/curso/IFCT0209/...
    ref = models.CharField(max_length=200, blank=True, default="")       # document.referrer
    meta = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    client_ts = models.DateTimeField(null=True, blank=True)              # ts от клиента (опционально)
    delta_sec = models.PositiveIntegerField(default=0)                    # !!! "tiempos entre cada clicado"

    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["curso_codigo", "user", "-created_at"]),
            models.Index(fields=["session_id", "user", "-created_at"]),
            models.Index(fields=["event", "-created_at"]),
        ]
