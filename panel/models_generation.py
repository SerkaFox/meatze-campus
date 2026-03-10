from django.conf import settings
from django.db import models


def generation_upload_to(instance, filename):
    return f"generations/source/{instance.user_id}/{filename}"


def generation_result_to(instance, filename):
    return f"generations/result/{instance.user_id}/{filename}"


def generation_asset_to(instance, filename):
    return f"generations/assets/{instance.user_id}/{filename}"


class GenerationAsset(models.Model):
    KIND_IMAGE = "image"
    KIND_VIDEO = "video"
    KIND_CHOICES = [
        (KIND_IMAGE, "Image"),
        (KIND_VIDEO, "Video"),
    ]

    ORIGIN_UPLOAD = "upload"
    ORIGIN_GENERATED = "generated"
    ORIGIN_CHOICES = [
        (ORIGIN_UPLOAD, "Upload"),
        (ORIGIN_GENERATED, "Generated"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generation_assets",
    )
    file = models.FileField(upload_to=generation_asset_to)

    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    origin = models.CharField(max_length=16, choices=ORIGIN_CHOICES, default=ORIGIN_UPLOAD)

    title = models.CharField(max_length=255, blank=True, default="")
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Asset #{self.pk} · {self.user_id} · {self.kind}"


class VideoGenerationJob(models.Model):
    STATUS_NEW = "new"
    STATUS_SUBMITTED = "submitted"
    STATUS_RUNNING = "running"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_RUNNING, "Running"),
        (STATUS_DONE, "Done"),
        (STATUS_ERROR, "Error"),
    ]

    QUALITY_LOW = "low"
    QUALITY_MEDIUM = "medium"
    QUALITY_HIGH = "high"
    QUALITY_CHOICES = [
        (QUALITY_LOW, "Low"),
        (QUALITY_MEDIUM, "Medium"),
        (QUALITY_HIGH, "High"),
    ]

    ASPECT_ORIGINAL = "original"
    ASPECT_16_9 = "16:9"
    ASPECT_CHOICES = [
        (ASPECT_ORIGINAL, "Original"),
        (ASPECT_16_9, "16:9"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="video_generations",
    )

    source_image = models.ImageField(upload_to=generation_upload_to, blank=True, null=True)
    source_asset = models.ForeignKey(
        GenerationAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_in_video_jobs",
    )

    result_file = models.FileField(upload_to=generation_result_to, blank=True, null=True)
    result_asset = models.ForeignKey(
        GenerationAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="video_result_jobs",
    )
    last_frame_asset = models.ForeignKey(
        GenerationAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="video_last_frame_jobs",
    )

    prompt = models.TextField()
    seconds = models.PositiveIntegerField(default=8)
    quality = models.CharField(max_length=12, choices=QUALITY_CHOICES, default=QUALITY_MEDIUM)
    aspect_ratio = models.CharField(max_length=20, choices=ASPECT_CHOICES, default=ASPECT_ORIGINAL)
    job_type = models.CharField(
        max_length=16,
        choices=[("video", "Video"), ("image", "Image")],
        default="video",
    )

    orig_width = models.PositiveIntegerField(default=0)
    orig_height = models.PositiveIntegerField(default=0)
    fit_width = models.PositiveIntegerField(default=0)
    fit_height = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_NEW)
    comfy_prompt_id = models.CharField(max_length=128, blank=True, default="")
    comfy_client_id = models.CharField(max_length=128, blank=True, default="")
    seed = models.BigIntegerField(default=0)
    error_text = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"VideoGenerationJob #{self.pk} · {self.user_id} · {self.status}"


class ImageGenerationJob(models.Model):
    STATUS_NEW = "new"
    STATUS_SUBMITTED = "submitted"
    STATUS_RUNNING = "running"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_RUNNING, "Running"),
        (STATUS_DONE, "Done"),
        (STATUS_ERROR, "Error"),
    ]

    QUALITY_LOW = "low"
    QUALITY_MEDIUM = "medium"
    QUALITY_HIGH = "high"
    QUALITY_CHOICES = [
        (QUALITY_LOW, "Low"),
        (QUALITY_MEDIUM, "Medium"),
        (QUALITY_HIGH, "High"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="image_generations",
    )

    source_image_1 = models.ImageField(upload_to=generation_upload_to, blank=True, null=True)
    source_image_2 = models.ImageField(upload_to=generation_upload_to, blank=True, null=True)
    source_image_3 = models.ImageField(upload_to=generation_upload_to, blank=True, null=True)

    source_asset_1 = models.ForeignKey(
        GenerationAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_as_image_ref_1",
    )
    source_asset_2 = models.ForeignKey(
        GenerationAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_as_image_ref_2",
    )
    source_asset_3 = models.ForeignKey(
        GenerationAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_as_image_ref_3",
    )

    result_image = models.ImageField(upload_to=generation_result_to, blank=True, null=True)
    result_asset = models.ForeignKey(
        GenerationAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="image_result_jobs",
    )

    prompt = models.TextField()
    quality = models.CharField(max_length=12, choices=QUALITY_CHOICES, default=QUALITY_MEDIUM)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_NEW)

    comfy_prompt_id = models.CharField(max_length=128, blank=True, default="")
    comfy_client_id = models.CharField(max_length=128, blank=True, default="")
    seed = models.BigIntegerField(default=0)
    error_text = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ImageGenerationJob #{self.pk} · {self.user_id} · {self.status}"