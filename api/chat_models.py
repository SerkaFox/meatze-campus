# api/models.py
from django.conf import settings
from django.db import models


class ChatMessage(models.Model):
    codigo = models.CharField(max_length=64, db_index=True)  # код курса
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    author_name = models.CharField(max_length=160)
    author_email = models.EmailField(max_length=190)
    body = models.TextField(blank=True, null=True)
    file = models.FileField(
        upload_to="chat_files/%Y/%m/%d",
        blank=True,
        null=True,
    )
    meta_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        ordering = ["id"]


class ChatRead(models.Model):
    codigo = models.CharField(max_length=64)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_msg_id = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("codigo", "user")


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
