from django.conf import settings
from django.db import models
from django.db.models import Q

# ===== Chat constants (ВАЖНО: на уровне модуля) =====
CHAT_KIND_COURSE = "course"
CHAT_KIND_DM = "dm"

CHAT_KIND_CHOICES = [
    (CHAT_KIND_COURSE, "Course"),
    (CHAT_KIND_DM, "Direct"),
]

class ChatMessage(models.Model):
    codigo = models.CharField(max_length=64, db_index=True)
    kind = models.CharField(
        max_length=16,
        choices=CHAT_KIND_CHOICES,
        default=CHAT_KIND_COURSE,
        db_index=True,
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    author_name = models.CharField(max_length=160)
    author_email = models.EmailField(max_length=190)

    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_dm_inbox",
        db_index=True,
    )

    thread_key = models.CharField(max_length=120, db_index=True, default="")

    body = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="chat_files/%Y/%m/%d", blank=True, null=True)
    meta_json = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["codigo", "kind", "created_at"]),
            models.Index(fields=["thread_key", "created_at"]),
            models.Index(fields=["codigo", "kind", "id"]),
        ]
        constraints = [
            models.CheckConstraint(
                name="chatmsg_course_to_user_null",
                condition=Q(kind=CHAT_KIND_COURSE, to_user__isnull=True) | ~Q(kind=CHAT_KIND_COURSE),
            ),
            models.CheckConstraint(
                name="chatmsg_dm_to_user_not_null",
                condition=Q(kind=CHAT_KIND_DM, to_user__isnull=False) | ~Q(kind=CHAT_KIND_DM),
            ),
        ]

class ChatRead(models.Model):
    codigo = models.CharField(max_length=64, db_index=True)
    kind = models.CharField(
        max_length=16,
        choices=CHAT_KIND_CHOICES,
        default=CHAT_KIND_COURSE,
        db_index=True,
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    peer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_reads_peer",
        db_index=True,
    )

    last_msg_id = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["codigo", "kind"]),
            models.Index(fields=["user", "codigo", "kind"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo", "user", "kind"],
                condition=Q(kind=CHAT_KIND_COURSE, peer_user__isnull=True),
                name="uniq_chatread_course",
            ),
            models.UniqueConstraint(
                fields=["codigo", "user", "kind", "peer_user"],
                condition=Q(kind=CHAT_KIND_DM, peer_user__isnull=False),
                name="uniq_chatread_dm",
            ),
            models.CheckConstraint(
                name="chatread_course_peer_null",
                condition=Q(kind=CHAT_KIND_COURSE, peer_user__isnull=True) | ~Q(kind=CHAT_KIND_COURSE),
            ),
            models.CheckConstraint(
                name="chatread_dm_peer_not_null",
                condition=Q(kind=CHAT_KIND_DM, peer_user__isnull=False) | ~Q(kind=CHAT_KIND_DM),
            ),
        ]



class ChatReaction(models.Model):
    msg = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("msg", "user", "emoji")
        indexes = [
            models.Index(fields=["msg"]),
        ]
