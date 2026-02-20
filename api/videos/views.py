from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Max
from django.contrib.auth.decorators import login_required

from .models import Video, Playlist, PlaylistItem

def _get_active_playlist(request, playlists_qs):
    """
    Выбираем активный плейлист:
    1) из GET ?pl=
    2) иначе из session
    3) иначе первый плейлист пользователя
    """
    pl_id = request.GET.get("pl")
    if pl_id:
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

@login_required
def mini_player(request):
    playlists = Playlist.objects.filter(owner=request.user).order_by("-creado", "-id")
    active_pl = _get_active_playlist(request, playlists)

    # Видео для выбранного плейлиста
    if active_pl:
        items = (PlaylistItem.objects
                 .select_related("video")
                 .filter(playlist=active_pl, video__activo=True)
                 .order_by("orden", "id"))
        qs_videos = [it.video for it in items]
    else:
        qs_videos = []

    out = [{
        "id": v.id,
        "title": v.titulo,
        "url": v.url,
        "poster": v.poster.url if v.poster else "",
    } for v in qs_videos]

    # Для админ-списка удаления/добавления можно показать все твои видео:
    my_all_videos = Video.objects.filter(owner=request.user, activo=True).order_by("orden", "id")

    return render(request, "videos/mini_player_admin.html", {
        "videos": out,                  # то, что играет в плеере (текущий плейлист)
        "videos_qs": my_all_videos,     # все твои видео (для управления)
        "playlists": playlists,
        "active_pl": active_pl,
    })

@login_required
@require_POST
def playlist_create(request):
    titulo = (request.POST.get("titulo") or "Lista").strip()
    pl = Playlist.objects.create(owner=request.user, titulo=titulo, is_public=False)
    request.session["videos_active_pl"] = pl.id
    messages.success(request, f"Lista creada: {pl.titulo}")
    return redirect(f"/videos/mini-player/?pl={pl.id}")

@login_required
@require_POST
def playlist_toggle_public(request, playlist_id: int):
    pl = get_object_or_404(Playlist, id=playlist_id, owner=request.user)
    pl.is_public = not pl.is_public
    pl.save(update_fields=["is_public"])
    return redirect(f"/videos/mini-player/?pl={pl.id}")

from django.db.models import Max
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect
from .models import Video, Playlist, PlaylistItem

@login_required
@require_POST
def video_upload(request):
    titulo = (request.POST.get("titulo") or "").strip()
    files = request.FILES.getlist("archivo")
    playlist_id = request.POST.get("playlist_id")

    if not files:
        messages.error(request, "Selecciona uno o varios archivos de vídeo.")
        return redirect("mini_player")

    pl = None
    if playlist_id:
        pl = Playlist.objects.filter(id=playlist_id, owner=request.user).first()

    # стартовый order для библиотеки
    last_order = Video.objects.filter(owner=request.user).aggregate(Max("orden")).get("orden__max") or 0

    created = 0
    for f in files:
        last_order += 1
        v = Video.objects.create(
            owner=request.user,
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
def playlist_add(request, playlist_id: int, video_id: int):
    pl = get_object_or_404(Playlist, id=playlist_id, owner=request.user)
    v = get_object_or_404(Video, id=video_id, owner=request.user)
    last = PlaylistItem.objects.filter(playlist=pl).aggregate(Max("orden")).get("orden__max") or 0
    PlaylistItem.objects.get_or_create(playlist=pl, video=v, defaults={"orden": last + 1})
    return redirect(f"/videos/mini-player/?pl={pl.id}")

@login_required
@require_POST
def playlist_remove(request, playlist_id: int, video_id: int):
    pl = get_object_or_404(Playlist, id=playlist_id, owner=request.user)
    PlaylistItem.objects.filter(playlist=pl, video_id=video_id).delete()
    return redirect(f"/videos/mini-player/?pl={pl.id}")

@login_required
@require_POST
def video_delete(request, video_id: int):
    v = get_object_or_404(Video, id=video_id, owner=request.user)
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

    # Можно использовать твой текущий mini_player.html
    return render(request, "videos/mini_player.html", {"videos": out})