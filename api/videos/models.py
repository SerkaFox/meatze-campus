# app/videos/models.py
from django.db import models
from django.conf import settings
import secrets

def video_upload_to(instance, filename):
    return f"videos/{instance.owner_id}/{filename}"

class Video(models.Model):
    owner = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="videos",
    null=True,          # <-- добавить
    blank=True
)
    titulo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to=video_upload_to)
    poster = models.ImageField(upload_to="videos/posters/", blank=True, null=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["orden", "id"]

    @property
    def url(self):
        return self.archivo.url

    def __str__(self):
        return self.titulo


class Playlist(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists")
    titulo = models.CharField(max_length=255, default="Lista")
    share_token = models.CharField(max_length=64, unique=True, blank=True)
    is_public = models.BooleanField(default=False)  # публичная по токену
    creado = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="items")
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        unique_together = ("playlist", "video")