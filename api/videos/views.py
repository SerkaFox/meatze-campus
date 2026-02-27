# api/videos/views.py
from __future__ import annotations

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Max
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from api.videos.models import Video, Playlist, PlaylistItem, HelpBinding


# -----------------------------
# access policy (single-owner)
# -----------------------------
def _admin_only(request):
    """
    В режиме "без owner" это обязательно, иначе любой залогиненный увидит/удалит всё.
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden("Solo para administradores.")
    return None


def _get_active_playlist(request, playlists_qs):
    """
    Выбираем активный плейлист:
    1) из GET ?pl=
    2) иначе из session
    3) иначе первый плейлист
    """
    pl_id = request.GET.get("pl")
    if pl_id and str(pl_id).isdigit():
        request.session["videos_active_pl"] = int(pl_id)
    else:
        pl_id = request.session.get("videos_active_pl")

    pl = None
    if pl_id:
        pl = playlists_qs.filter(id=pl_id).first()

    if not pl:
        pl = playlists_qs.first()
        if pl:
            request.session["videos_active_pl"] = pl.id

    return pl


# -----------------------------
# admin mini player
# -----------------------------
@login_required
def mini_player(request):
    deny = _admin_only(request)
    if deny:
        return deny

    playlists = Playlist.objects.all().order_by("-creado", "-id")
    active_pl = _get_active_playlist(request, playlists)

    # Видео для выбранного плейлиста
    if active_pl:
        items = (PlaylistItem.objects
                 .select_related("video")
                 .filter(playlist=active_pl, video__activo=True)
                 .order_by("orden", "id"))
        pl_videos = [it.video for it in items]
    else:
        pl_videos = []

    out = [{
        "id": v.id,
        "title": v.titulo,
        "url": v.url,
        "poster": v.poster.url if v.poster else "",
    } for v in pl_videos]

    # библиотека (все активные видео)
    my_all_videos = Video.objects.filter(activo=True).order_by("orden", "id")

    # help bindings для активного плейлиста
    bindings = []
    if active_pl:
        bindings = (HelpBinding.objects
                    .filter(playlist=active_pl)
                    .select_related("start_video")
                    .order_by("priority", "id"))

    return render(request, "videos/mini_player_admin.html", {
        "videos": out,                  # то, что играет в плеере (текущий плейлист)
        "videos_qs": my_all_videos,     # библиотека
        "playlists": playlists,
        "active_pl": active_pl,

        # help-admin context
        "help_bindings": bindings,
        "help_roles": HelpBinding.ROLE_CHOICES,
        "pl_videos": pl_videos,  # чтобы выбрать start_video из видео плейлиста
    })


# -----------------------------
# playlists admin actions
# -----------------------------
@login_required
@require_POST
def playlist_create(request):
    deny = _admin_only(request)
    if deny:
        return deny

    titulo = (request.POST.get("titulo") or "Lista").strip()
    pl = Playlist.objects.create(titulo=titulo, is_public=False)
    request.session["videos_active_pl"] = pl.id
    messages.success(request, f"Lista creada: {pl.titulo}")
    return redirect(f"/videos/mini-player/?pl={pl.id}")


@login_required
@require_POST
def playlist_toggle_public(request, playlist_id: int):
    deny = _admin_only(request)
    if deny:
        return deny

    pl = get_object_or_404(Playlist, id=playlist_id)
    pl.is_public = not pl.is_public
    pl.save(update_fields=["is_public"])
    return redirect(f"/videos/mini-player/?pl={pl.id}")


@login_required
@require_POST
def playlist_add(request, playlist_id: int, video_id: int):
    deny = _admin_only(request)
    if deny:
        return deny

    pl = get_object_or_404(Playlist, id=playlist_id)
    v = get_object_or_404(Video, id=video_id)

    last = PlaylistItem.objects.filter(playlist=pl).aggregate(Max("orden")).get("orden__max") or 0
    PlaylistItem.objects.get_or_create(playlist=pl, video=v, defaults={"orden": last + 1})
    return redirect(f"/videos/mini-player/?pl={pl.id}")


@login_required
@require_POST
def playlist_remove(request, playlist_id: int, video_id: int):
    deny = _admin_only(request)
    if deny:
        return deny

    pl = get_object_or_404(Playlist, id=playlist_id)
    PlaylistItem.objects.filter(playlist=pl, video_id=video_id).delete()
    return redirect(f"/videos/mini-player/?pl={pl.id}")


# -----------------------------
# video admin actions
# -----------------------------
@login_required
@require_POST
def video_upload(request):
    deny = _admin_only(request)
    if deny:
        return deny

    titulo = (request.POST.get("titulo") or "").strip()
    files = request.FILES.getlist("archivo")
    playlist_id = request.POST.get("playlist_id")

    if not files:
        messages.error(request, "Selecciona uno o varios archivos de vídeo.")
        return redirect("mini_player")

    pl = None
    if playlist_id and str(playlist_id).isdigit():
        pl = Playlist.objects.filter(id=int(playlist_id)).first()

    # стартовый order для библиотеки
    last_order = Video.objects.aggregate(Max("orden")).get("orden__max") or 0

    created = 0
    for f in files:
        last_order += 1
        v = Video.objects.create(
            titulo=(titulo if (titulo and len(files) == 1) else f.name),
            archivo=f,
            orden=last_order,
            activo=True
        )
        created += 1

        if pl:
            last_pl = PlaylistItem.objects.filter(playlist=pl).aggregate(Max("orden")).get("orden__max") or 0
            PlaylistItem.objects.get_or_create(
                playlist=pl,
                video=v,
                defaults={"orden": last_pl + 1}
            )

    if pl:
        messages.success(request, f"Subidos {created} vídeo(s) y añadidos a «{pl.titulo}».")
        return redirect(f"/videos/mini-player/?pl={pl.id}")

    messages.success(request, f"Subidos {created} vídeo(s).")
    return redirect("mini_player")


@login_required
@require_POST
def video_delete(request, video_id: int):
    deny = _admin_only(request)
    if deny:
        return deny

    v = get_object_or_404(Video, id=video_id)
    storage = v.archivo.storage
    path = v.archivo.name

    with transaction.atomic():
        v.delete()
        if path:
            try:
                storage.delete(path)
            except Exception:
                pass

    messages.success(request, "Vídeo eliminado.")
    return redirect("mini_player")


# -----------------------------
# public playlist view
# -----------------------------
def playlist_public(request, token: str):
    pl = get_object_or_404(Playlist, share_token=token, is_public=True)

    items = (PlaylistItem.objects
             .select_related("video")
             .filter(playlist=pl, video__activo=True)
             .order_by("orden", "id"))

    out = [{
        "id": it.video.id,
        "title": it.video.titulo,
        "url": it.video.url,
        "poster": it.video.poster.url if it.video.poster else "",
    } for it in items]

    return render(request, "videos/mini_player.html", {"videos": out})


def playlist_embed(request, token: str):
    pl = get_object_or_404(Playlist, share_token=token, is_public=True)

    items = (PlaylistItem.objects
             .select_related("video")
             .filter(playlist=pl, video__activo=True)
             .order_by("orden", "id"))

    start_vid = (request.GET.get("vid") or "").strip()
    autoplay  = (request.GET.get("autoplay") == "1")

    # only_one: либо явно only=1, либо автоматически если передан vid
    only_one = (request.GET.get("only") == "1") or (start_vid.isdigit())

    if only_one and start_vid.isdigit():
        items = items.filter(video_id=int(start_vid))

    out = [{
        "id": it.video.id,
        "title": it.video.titulo,
        "url": it.video.url,
        "poster": it.video.poster.url if it.video.poster else "",
    } for it in items]

    return render(request, "videos/embed_player.html", {
        "videos": out,
        "start_vid": start_vid,
        "autoplay": autoplay,
        "pl_title": pl.titulo,
        "only_one": only_one,
    })


# -----------------------------
# help bindings admin
# -----------------------------
@login_required
@require_POST
def helpbinding_create(request):
    deny = _admin_only(request)
    if deny:
        return deny

    playlist_id = request.POST.get("playlist_id")
    if not playlist_id or not str(playlist_id).isdigit():
        return redirect("mini_player")

    pl = get_object_or_404(Playlist, id=int(playlist_id))

    role = (request.POST.get("role") or "guest").strip()
    path = (request.POST.get("path") or "").strip()
    query_contains = (request.POST.get("query_contains") or "").strip()
    title = (request.POST.get("title") or "").strip()
    priority = int(request.POST.get("priority") or 100)

    start_video_id = request.POST.get("start_video_id") or ""
    start_video = None
    if start_video_id and str(start_video_id).isdigit():
        start_video = Video.objects.filter(id=int(start_video_id)).first()

    if path and not path.startswith("/"):
        path = "/" + path

    HelpBinding.objects.create(
        playlist=pl,
        role=role,
        path=path,
        query_contains=query_contains,
        title=title,
        priority=priority,
        start_video=start_video,
        is_active=True
    )
    return redirect(f"/videos/mini-player/?pl={pl.id}")


@login_required
@require_POST
def helpbinding_update(request, binding_id: int):
    deny = _admin_only(request)
    if deny:
        return deny

    hb = get_object_or_404(HelpBinding, id=binding_id)

    hb.role = (request.POST.get("role") or hb.role).strip()
    hb.path = (request.POST.get("path") or hb.path).strip()
    hb.query_contains = (request.POST.get("query_contains") or "").strip()
    hb.title = (request.POST.get("title") or "").strip()
    hb.priority = int(request.POST.get("priority") or hb.priority)

    start_video_id = request.POST.get("start_video_id") or ""
    if start_video_id and str(start_video_id).isdigit():
        hb.start_video = Video.objects.filter(id=int(start_video_id)).first()
    else:
        hb.start_video = None

    if hb.path and not hb.path.startswith("/"):
        hb.path = "/" + hb.path

    hb.save()
    return redirect(f"/videos/mini-player/?pl={hb.playlist_id}")


@login_required
@require_POST
def helpbinding_toggle(request, binding_id: int):
    deny = _admin_only(request)
    if deny:
        return deny

    hb = get_object_or_404(HelpBinding, id=binding_id)
    hb.is_active = not hb.is_active
    hb.save(update_fields=["is_active"])
    return redirect(f"/videos/mini-player/?pl={hb.playlist_id}")


@login_required
@require_POST
def helpbinding_delete(request, binding_id: int):
    deny = _admin_only(request)
    if deny:
        return deny

    hb = get_object_or_404(HelpBinding, id=binding_id)
    pl_id = hb.playlist_id
    hb.delete()
    return redirect(f"/videos/mini-player/?pl={pl_id}")