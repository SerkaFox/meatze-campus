# app/videos/models.py
from django.db import models

def video_upload_to(instance, filename):
    return f"videos/{filename}"

class Video(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=video_upload_to, blank=True, null=True)
    poster = models.ImageField(upload_to="videos/posters/", blank=True, null=True)

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    @property
    def url(self):
        return self.file.url if self.file else ""