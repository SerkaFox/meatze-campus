import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta

def default_room_secret():
    return secrets.token_urlsafe(16)

def default_expires():
    return timezone.now() + timedelta(days=7)

def upload_to(instance, filename):
    return f"shortshare/{instance.room.code}/{instance.id}/{filename}"

class ShortRoom(models.Model):
    code = models.CharField(max_length=8, db_index=True)
    secret = models.CharField(max_length=32, default=default_room_secret)  # <-- ВОТ
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    teacher_pin = models.CharField(max_length=16, blank=True, default="")

class ShortFile(models.Model):
    room = models.ForeignKey(ShortRoom, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to=upload_to)
    original_name = models.CharField(max_length=255)
    size = models.BigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expires, db_index=True)
    
# shortshare/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.validators import URLValidator

def default_link_expires():
    return timezone.now() + timedelta(minutes=30)

class ShortLink(models.Model):
    room = models.ForeignKey("ShortRoom", on_delete=models.CASCADE, related_name="links")
    url = models.URLField(max_length=1000, validators=[URLValidator()])
    title = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_link_expires, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["room", "expires_at"]),
        ]