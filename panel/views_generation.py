import json
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .forms_generation import ImageGenerationForm, VideoGenerationForm
from .models_generation import GenerationAsset, ImageGenerationJob, VideoGenerationJob
from .utils_comfy_video import (
    WORKFLOW_IMAGE,
    WORKFLOW_VIDEO,
    extract_last_frame,
    fetch_file_bytes,
    get_history,
    inspect_image_for_photo,
    inspect_image_for_video,
    make_seed,
    patch_image_workflow,
    patch_video_workflow,
    pick_image_result,
    pick_video_result,
    queue_prompt,
    read_workflow,
    upload_image_file,
)


def _create_asset_from_uploaded_image(user, django_file, *, origin="upload", title="") -> GenerationAsset:
    asset = GenerationAsset.objects.create(
        user=user,
        file=django_file,
        kind=GenerationAsset.KIND_IMAGE,
        origin=origin,
        title=title or os.path.basename(django_file.name),
    )
    try:
        from PIL import Image
        with Image.open(asset.file.path) as img:
            asset.width, asset.height = img.size
        asset.save(update_fields=["width", "height"])
    except Exception:
        pass
    return asset


def _create_asset_from_bytes(user, *, blob: bytes, filename: str, kind: str, origin="generated", title="") -> GenerationAsset:
    asset = GenerationAsset.objects.create(
        user=user,
        kind=kind,
        origin=origin,
        title=title or filename,
    )
    asset.file.save(filename, ContentFile(blob), save=True)

    if kind == GenerationAsset.KIND_IMAGE:
        try:
            from PIL import Image
            with Image.open(asset.file.path) as img:
                asset.width, asset.height = img.size
            asset.save(update_fields=["width", "height"])
        except Exception:
            pass
    return asset


def _resolve_video_source(job: VideoGenerationJob) -> tuple[str, str]:
    if job.source_image:
        return job.source_image.path, os.path.basename(job.source_image.name)
    if job.source_asset and job.source_asset.file:
        return job.source_asset.file.path, os.path.basename(job.source_asset.file.name)
    raise ValueError("No video source image selected")


def _resolve_image_sources(job: ImageGenerationJob) -> list[tuple[str, str]]:
    refs = []

    direct = [
        job.source_image_1,
        job.source_image_2,
        job.source_image_3,
    ]
    assets = [
        job.source_asset_1,
        job.source_asset_2,
        job.source_asset_3,
    ]

    for f in direct:
        if f:
            refs.append((f.path, os.path.basename(f.name)))

    for a in assets:
        if a and a.file:
            refs.append((a.file.path, os.path.basename(a.file.name)))

    uniq = []
    seen = set()
    for path, name in refs:
        if path not in seen:
            uniq.append((path, name))
            seen.add(path)

    return uniq[:3]


@login_required
@require_GET
def video_generation_page(request):
    video_form = VideoGenerationForm()
    image_form = ImageGenerationForm()
    assets = GenerationAsset.objects.filter(user=request.user, kind=GenerationAsset.KIND_IMAGE)[:40]
    video_jobs = VideoGenerationJob.objects.filter(user=request.user)[:20]
    image_jobs = ImageGenerationJob.objects.filter(user=request.user)[:20]

    return render(
        request,
        "panel/video_generation.html",
        {
            "video_form": video_form,
            "image_form": image_form,
            "assets": assets,
            "video_jobs": video_jobs,
            "image_jobs": image_jobs,
        },
    )


@login_required
@require_GET
def generation_assets_list(request):
    assets = GenerationAsset.objects.filter(user=request.user, kind=GenerationAsset.KIND_IMAGE)[:100]
    return JsonResponse(
        {
            "ok": True,
            "items": [
                {
                    "id": a.id,
                    "url": a.file.url,
                    "title": a.title,
                    "width": a.width,
                    "height": a.height,
                    "origin": a.origin,
                    "created_at": a.created_at.isoformat(),
                }
                for a in assets
            ],
        }
    )


@login_required
@require_POST
def video_generation_create(request):
    form = VideoGenerationForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    job = form.save(commit=False)
    job.user = request.user
    job.seed = make_seed()
    job.job_type = "video"

    source_asset_id = form.cleaned_data.get("source_asset_id")
    if source_asset_id and not request.FILES.get("source_image"):
        asset = get_object_or_404(GenerationAsset, pk=source_asset_id, user=request.user, kind=GenerationAsset.KIND_IMAGE)
        job.source_asset = asset

    job.save()

    if job.source_image:
        source_asset = _create_asset_from_uploaded_image(
            request.user,
            job.source_image,
            origin=GenerationAsset.ORIGIN_UPLOAD,
            title=os.path.basename(job.source_image.name),
        )
        job.source_asset = source_asset
        job.save(update_fields=["source_asset", "updated_at"])

    source_path, source_name = _resolve_video_source(job)

    ow, oh, fw, fh = inspect_image_for_video(
        source_path,
        job.quality,
        aspect_ratio=job.aspect_ratio,
    )
    job.orig_width = ow
    job.orig_height = oh
    job.fit_width = fw
    job.fit_height = fh

    workflow = read_workflow(WORKFLOW_VIDEO)
    uploaded_name = upload_image_file(source_path, source_name)
    client_id = str(uuid.uuid4())

    prompt = patch_video_workflow(
        workflow,
        prompt=job.prompt,
        image_name=uploaded_name,
        width=job.fit_width,
        height=job.fit_height,
        seconds=job.seconds,
        seed=job.seed,
    )
    prompt_id = queue_prompt(prompt, client_id)

    job.comfy_client_id = client_id
    job.comfy_prompt_id = prompt_id
    job.status = VideoGenerationJob.STATUS_SUBMITTED
    job.save(
        update_fields=[
            "orig_width",
            "orig_height",
            "fit_width",
            "fit_height",
            "comfy_client_id",
            "comfy_prompt_id",
            "status",
            "updated_at",
        ]
    )

    return JsonResponse({"ok": True, "job": serialize_video_job(job)})


@login_required
@require_POST
def image_generation_create(request):
    form = ImageGenerationForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    job = form.save(commit=False)
    job.user = request.user
    job.seed = make_seed()

    aid1 = form.cleaned_data.get("source_asset_1_id")
    aid2 = form.cleaned_data.get("source_asset_2_id")
    aid3 = form.cleaned_data.get("source_asset_3_id")

    if aid1 and not request.FILES.get("source_image_1"):
        job.source_asset_1 = get_object_or_404(GenerationAsset, pk=aid1, user=request.user, kind=GenerationAsset.KIND_IMAGE)
    if aid2 and not request.FILES.get("source_image_2"):
        job.source_asset_2 = get_object_or_404(GenerationAsset, pk=aid2, user=request.user, kind=GenerationAsset.KIND_IMAGE)
    if aid3 and not request.FILES.get("source_image_3"):
        job.source_asset_3 = get_object_or_404(GenerationAsset, pk=aid3, user=request.user, kind=GenerationAsset.KIND_IMAGE)

    job.save()

    for field_name, title in [
        ("source_image_1", "image_ref_1"),
        ("source_image_2", "image_ref_2"),
        ("source_image_3", "image_ref_3"),
    ]:
        f = getattr(job, field_name)
        if f:
            asset = _create_asset_from_uploaded_image(
                request.user,
                f,
                origin=GenerationAsset.ORIGIN_UPLOAD,
                title=title,
            )
            setattr(job, field_name.replace("image", "asset"), asset)

    job.save()

    refs = _resolve_image_sources(job)
    if not refs:
        job.status = ImageGenerationJob.STATUS_ERROR
        job.error_text = "No image references selected"
        job.save(update_fields=["status", "error_text", "updated_at"])
        return JsonResponse({"ok": False, "error": "No image references selected"}, status=400)

    workflow = read_workflow(WORKFLOW_IMAGE)
    uploaded_names = []
    for path, name in refs:
        uploaded_names.append(upload_image_file(path, name))

    while len(uploaded_names) < 3:
        uploaded_names.append(uploaded_names[-1])

    client_id = str(uuid.uuid4())
    prompt = patch_image_workflow(
        workflow,
        prompt=job.prompt,
        image_names=uploaded_names,
        seed=job.seed,
    )
    prompt_id = queue_prompt(prompt, client_id)

    job.comfy_client_id = client_id
    job.comfy_prompt_id = prompt_id
    job.status = ImageGenerationJob.STATUS_SUBMITTED
    job.save(update_fields=["comfy_client_id", "comfy_prompt_id", "status", "updated_at"])

    return JsonResponse({"ok": True, "job": serialize_image_job(job)})


@login_required
@require_GET
def video_generation_status(request, pk: int):
    job = get_object_or_404(VideoGenerationJob, pk=pk, user=request.user)

    if job.status in [VideoGenerationJob.STATUS_DONE, VideoGenerationJob.STATUS_ERROR]:
        return JsonResponse({"ok": True, "job": serialize_video_job(job)})

    if not job.comfy_prompt_id:
        return JsonResponse({"ok": True, "job": serialize_video_job(job)})

    history = get_history(job.comfy_prompt_id)
    item = history.get(job.comfy_prompt_id)

    if item and item.get("outputs"):
        result = pick_video_result(item)
        if result and not job.result_file:
            blob = fetch_file_bytes(
                result["filename"],
                result.get("subfolder", ""),
                result.get("type", "output"),
            )
            filename = result.get("filename", f"video_job_{job.pk}.mp4")
            if not filename.lower().endswith((".mp4", ".mov", ".webm", ".gif")):
                filename += ".mp4"

            job.result_file.save(filename, ContentFile(blob), save=False)
            job.status = VideoGenerationJob.STATUS_DONE
            job.save(update_fields=["result_file", "status", "updated_at"])

            video_asset = _create_asset_from_bytes(
                request.user,
                blob=blob,
                filename=filename,
                kind=GenerationAsset.KIND_VIDEO,
                origin=GenerationAsset.ORIGIN_GENERATED,
                title=f"video_job_{job.pk}",
            )
            job.result_asset = video_asset

            try:
                media_root = Path(settings.MEDIA_ROOT)
                tmp_frames_dir = media_root / "generations" / "tmp_last_frames" / str(request.user.id)
                tmp_frames_dir.mkdir(parents=True, exist_ok=True)
                frame_path = tmp_frames_dir / f"video_job_{job.pk}_last.jpg"

                extract_last_frame(job.result_file.path, str(frame_path))

                with open(frame_path, "rb") as fh:
                    frame_asset = GenerationAsset.objects.create(
                        user=request.user,
                        kind=GenerationAsset.KIND_IMAGE,
                        origin=GenerationAsset.ORIGIN_GENERATED,
                        title=f"video_job_{job.pk}_last_frame",
                    )
                    frame_asset.file.save(frame_path.name, File(fh), save=True)

                try:
                    from PIL import Image
                    with Image.open(frame_asset.file.path) as img:
                        frame_asset.width, frame_asset.height = img.size
                    frame_asset.save(update_fields=["width", "height"])
                except Exception:
                    pass

                job.last_frame_asset = frame_asset
            except Exception as e:
                job.error_text = f"{job.error_text}\nLast frame extract failed: {e}".strip()

            job.save(update_fields=["result_asset", "last_frame_asset", "error_text", "updated_at"])

    elif item and item.get("status", {}).get("status_str") == "error":
        job.status = VideoGenerationJob.STATUS_ERROR
        job.error_text = json.dumps(item.get("status", {}), ensure_ascii=False)
        job.save(update_fields=["status", "error_text", "updated_at"])
    else:
        job.status = VideoGenerationJob.STATUS_RUNNING if item else VideoGenerationJob.STATUS_SUBMITTED
        job.save(update_fields=["status", "updated_at"])

    return JsonResponse({"ok": True, "job": serialize_video_job(job)})


@login_required
@require_GET
def image_generation_status(request, pk: int):
    job = get_object_or_404(ImageGenerationJob, pk=pk, user=request.user)

    if job.status in [ImageGenerationJob.STATUS_DONE, ImageGenerationJob.STATUS_ERROR]:
        return JsonResponse({"ok": True, "job": serialize_image_job(job)})

    if not job.comfy_prompt_id:
        return JsonResponse({"ok": True, "job": serialize_image_job(job)})

    history = get_history(job.comfy_prompt_id)
    item = history.get(job.comfy_prompt_id)

    if item and item.get("outputs"):
        result = pick_image_result(item)
        if result and not job.result_image:
            blob = fetch_file_bytes(
                result["filename"],
                result.get("subfolder", ""),
                result.get("type", "output"),
            )
            filename = result.get("filename", f"image_job_{job.pk}.png")
            if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                filename += ".png"

            job.result_image.save(filename, ContentFile(blob), save=False)
            job.status = ImageGenerationJob.STATUS_DONE
            job.save(update_fields=["result_image", "status", "updated_at"])

            result_asset = _create_asset_from_bytes(
                request.user,
                blob=blob,
                filename=filename,
                kind=GenerationAsset.KIND_IMAGE,
                origin=GenerationAsset.ORIGIN_GENERATED,
                title=f"image_job_{job.pk}",
            )
            job.result_asset = result_asset
            job.save(update_fields=["result_asset", "updated_at"])

    elif item and item.get("status", {}).get("status_str") == "error":
        job.status = ImageGenerationJob.STATUS_ERROR
        job.error_text = json.dumps(item.get("status", {}), ensure_ascii=False)
        job.save(update_fields=["status", "error_text", "updated_at"])
    else:
        job.status = ImageGenerationJob.STATUS_RUNNING if item else ImageGenerationJob.STATUS_SUBMITTED
        job.save(update_fields=["status", "updated_at"])

    return JsonResponse({"ok": True, "job": serialize_image_job(job)})


def serialize_video_job(job: VideoGenerationJob) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "prompt": job.prompt,
        "seconds": job.seconds,
        "quality": job.quality,
        "aspect_ratio": job.aspect_ratio,
        "created_at": job.created_at.isoformat(),
        "result_url": job.result_file.url if job.result_file else "",
        "error_text": job.error_text,
        "fit_width": job.fit_width,
        "fit_height": job.fit_height,
        "last_frame_url": job.last_frame_asset.file.url if job.last_frame_asset and job.last_frame_asset.file else "",
        "source_asset_id": job.source_asset_id or "",
    }


def serialize_image_job(job: ImageGenerationJob) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "prompt": job.prompt,
        "quality": job.quality,
        "created_at": job.created_at.isoformat(),
        "result_url": job.result_image.url if job.result_image else "",
        "error_text": job.error_text,
        "result_asset_id": job.result_asset_id or "",
    }