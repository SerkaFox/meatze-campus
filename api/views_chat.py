# api/views_chat.py
import mimetypes

from django.utils import timezone
from django.db import transaction
from django.db.models import Count
from django.conf import settings

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.models import Enrol
from api.models import ChatMessage, ChatRead, ChatReaction
from api.utils_temp import is_teacher  # уже есть
from panel.models import Curso
from django.db import models
from datetime import datetime, timezone as dt_timezone

from rest_framework.authentication import SessionAuthentication
import logging
logger = logging.getLogger(__name__)

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # отключаем CSRF check


ALLOWED_EXTS = {
    # imágenes
    "jpg", "jpeg", "jpe", "png", "gif", "webp", "heic", "heif",
    # documentos
    "pdf", "txt", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    # compresión
    "zip", "rar",
    # audio / video (по желанию)
    "mp3", "wav", "ogg", "mp4", "webm",
}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB
def _parse_kind(request) -> str:
    k = (request.query_params.get("kind") or request.data.get("kind") or "").strip().lower()
    if k in ("", "course", "curso", "general"):
        return "course"
    if k in ("dm", "direct", "privado", "teacher"):
        return "dm"
    return "course"

def _get_dm_peer(request, codigo: str):
    """
    DM peer зависит от того, кто пишет:
    - если пишет teacher -> peer должен быть student/alumno в этом курсе
    - если пишет student -> peer должен быть teacher в этом курсе
    """
    peer_id = request.query_params.get("peer_id") or request.data.get("peer_id")
    try:
        peer_id = int(peer_id or 0)
    except Exception:
        peer_id = 0
    if peer_id <= 0:
        return None

    me_is_teacher = bool(is_teacher(request.user))

    if me_is_teacher:
        allowed_roles = ["student", "alumno"]
    else:
        allowed_roles = ["teacher"]

    enrol = (
        Enrol.objects
        .select_related("user", "user__profile")
        .filter(codigo=codigo, role__in=allowed_roles, user_id=peer_id)
        .first()
    )
    return enrol.user if enrol else None

def _thread_key(codigo: str, kind: str, a_id: int, b_id: int | None = None) -> str:
    if kind == "course":
        return f"course:{codigo}"
    # dm
    lo, hi = (a_id, b_id) if a_id <= b_id else (b_id, a_id)
    return f"dm:{codigo}:{lo}:{hi}"


def _dm_scope_q(codigo: str, me_id: int, peer_id: int):
    # сообщения только между me и peer
    return models.Q(codigo=codigo, kind="dm", deleted_at__isnull=True) & (
        models.Q(user_id=me_id, to_user_id=peer_id) |
        models.Q(user_id=peer_id, to_user_id=me_id)
    )


def _is_course_member(user, codigo: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    return Enrol.objects.filter(
        user=user,
        codigo=codigo,
        role__in=["teacher", "student", "alumno"],
    ).exists()


def _chat_forbidden():
    return Response(
        {"detail": "Solo participantes del curso"},
        status=status.HTTP_403_FORBIDDEN,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def chat_messages(request, codigo: str):
    user = request.user
    codigo = (codigo or "").strip()
    if not _is_course_member(user, codigo):
        return _chat_forbidden()

    kind = _parse_kind(request)

    # --- DM peer (teacher) ---
    peer = None
    if kind == "dm":
        peer = _get_dm_peer(request, codigo)
        if not peer:
            return Response({"error": "teacher_id inválido o no es docente del curso"}, status=status.HTTP_400_BAD_REQUEST)

    # -------- GET: список сообщений --------
    if request.method == "GET":
        after_id = int(request.query_params.get("after_id") or 0)
        limit = int(request.query_params.get("limit") or 50)
        limit = max(1, min(100, limit))

        if kind == "course":
            qs = ChatMessage.objects.filter(
                codigo=codigo,
                kind="course",
                deleted_at__isnull=True,
                id__gt=after_id,
            ).order_by("id")[:limit]
        else:
            qs = ChatMessage.objects.filter(
                _dm_scope_q(codigo, user.id, peer.id),
                id__gt=after_id,
            ).order_by("id")[:limit]

        items = list(qs)
        ids = [m.id for m in items]

        reactions_map = {mid: [] for mid in ids}
        my_map = {mid: set() for mid in ids}

        if ids:
            agg = (
                ChatReaction.objects
                .filter(msg_id__in=ids)
                .values("msg_id", "emoji")
                .annotate(cnt=Count("id"))
            )
            for r in agg:
                reactions_map[r["msg_id"]].append(
                    {"emoji": r["emoji"], "count": r["cnt"], "me": 0}
                )

            mine = ChatReaction.objects.filter(msg_id__in=ids, user=user)
            for r in mine:
                my_map[r.msg_id].add(r.emoji)

            for mid, lst in reactions_map.items():
                mine_set = my_map.get(mid) or set()
                for rec in lst:
                    if rec["emoji"] in mine_set:
                        rec["me"] = 1

        def _msg_to_dict(m: ChatMessage):
            file_url = None
            if m.file and hasattr(m.file, "url"):
                file_url = request.build_absolute_uri(m.file.url)

            return {
                "id": m.id,
                "codigo": m.codigo,
                "kind": m.kind,
                "user_id": m.user_id,
                "to_user_id": m.to_user_id,
                "author_name": m.author_name,
                "author_email": m.author_email,
                "body": m.body or "",
                "file_url": file_url,
                "meta_json": m.meta_json or {},
                "ts": int(m.created_at.timestamp()),
                "reactions": reactions_map.get(m.id, []),
            }

        items_out = [_msg_to_dict(m) for m in items]
        last_id = items[-1].id if items else after_id

        return Response({"items": items_out, "last_id": last_id})

    # -------- POST: отправка сообщения --------
    body = (request.data.get("body") or "").strip()
    upload = request.FILES.get("file")
    meta = {}

    if upload:
        if upload.size > MAX_FILE_SIZE:
            return Response({"error": "Archivo demasiado grande (máx 15 MB)"}, status=status.HTTP_400_BAD_REQUEST)
        name = upload.name
        ext = (name.rsplit(".", 1)[-1] or "").lower()
        if ext not in ALLOWED_EXTS:
            return Response({"error": "Tipo de archivo no permitido"}, status=status.HTTP_400_BAD_REQUEST)

    if not body and not upload:
        return Response({"error": "Mensaje vacío"}, status=status.HTTP_400_BAD_REQUEST)
    if len(body) > 5000:
        body = body[:5000]

    msg = ChatMessage(
        codigo=codigo,
        kind=kind,
        user=user,
        to_user=(peer if kind == "dm" else None),
        thread_key=_thread_key(codigo, kind, user.id, (peer.id if peer else None)),
        author_name=getattr(user, "get_full_name", lambda: "")() or user.email or "",
        author_email=user.email or "",
        body=body or None,
        meta_json=meta or None,
    )
    if upload:
        msg.file = upload
    msg.save()

    return Response({"ok": 1, "id": msg.id})



@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def chat_react(request, codigo: str):
    user = request.user
    codigo = (codigo or "").strip()
    if not _is_course_member(user, codigo):
        return _chat_forbidden()

    msg_id = int(request.query_params.get("msg_id") or 0)
    emoji = (request.query_params.get("emoji") or "").strip()[:16]
    if msg_id <= 0 or not emoji:
        return Response({"error": "Parámetros"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        msg = ChatMessage.objects.get(id=msg_id, codigo=codigo)
    except ChatMessage.DoesNotExist:
        return Response({"error": "Mensaje no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    method = request.method.upper()

    with transaction.atomic():
        current = ChatReaction.objects.filter(msg=msg, user=user).first()

        if method == "DELETE":
            if current and current.emoji == emoji:
                current.delete()
            return Response({"ok": 1, "action": "removed"})

        # POST → toggle / replace
        if current:
            if current.emoji == emoji:
                current.delete()
                return Response({"ok": 1, "action": "removed"})
            else:
                current.delete()
        ChatReaction.objects.create(msg=msg, user=user, emoji=emoji)
        return Response({"ok": 1, "action": "added"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_read(request, codigo: str):
    user = request.user
    codigo = (codigo or "").strip()
    if not _is_course_member(user, codigo):
        return _chat_forbidden()

    kind = _parse_kind(request)

    peer = None
    if kind == "dm":
        peer = _get_dm_peer(request, codigo)
        if not peer:
            return Response({"error": "teacher_id inválido o no es docente del curso"}, status=status.HTTP_400_BAD_REQUEST)

    last_id = int(request.data.get("last_id") or 0)
    if last_id < 0:
        last_id = 0

    obj, _ = ChatRead.objects.get_or_create(
        codigo=codigo,
        kind=kind,
        user=user,
        peer_user=(peer if kind == "dm" else None),
        defaults={"last_msg_id": last_id},
    )
    if last_id > obj.last_msg_id:
        obj.last_msg_id = last_id
        obj.save(update_fields=["last_msg_id", "updated_at"])

    return Response({"ok": 1})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_unread(request, codigo: str):
    user = request.user
    codigo = (codigo or "").strip()
    if not _is_course_member(user, codigo):
        return _chat_forbidden()

    kind = _parse_kind(request)

    peer = None
    if kind == "dm":
        peer = _get_dm_peer(request, codigo)
        if not peer:
            return Response({"error": "teacher_id inválido o no es docente del curso"}, status=status.HTTP_400_BAD_REQUEST)

    last_seen = (
        ChatRead.objects.filter(
            codigo=codigo,
            kind=kind,
            user=user,
            peer_user=(peer if kind == "dm" else None),
        )
        .values_list("last_msg_id", flat=True)
        .first()
    ) or 0

    if kind == "course":
        qs = ChatMessage.objects.filter(codigo=codigo, kind="course", deleted_at__isnull=True)
        unread = qs.filter(id__gt=last_seen).count()
        latest = qs.aggregate(m=models.Max("id"))["m"] or 0
        return Response({"unread": unread, "last_seen": last_seen, "latest": latest})

    # dm:
    qs = ChatMessage.objects.filter(_dm_scope_q(codigo, user.id, peer.id))
    latest = qs.aggregate(m=models.Max("id"))["m"] or 0

    # непрочитанные = сообщения от teacher после last_seen
    unread = qs.filter(id__gt=last_seen, user_id=peer.id).count()
    return Response({"unread": unread, "last_seen": last_seen, "latest": latest})


from django.utils import timezone

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def chat_delete_message(request, codigo: str, msg_id: int):
    user = request.user
    codigo = (codigo or "").strip()
    if not _is_course_member(user, codigo):
        return _chat_forbidden()
    if not is_teacher(user):
        return Response({"detail": "Solo docentes"}, status=status.HTTP_403_FORBIDDEN)

    try:
        msg = ChatMessage.objects.get(id=msg_id, codigo=codigo, deleted_at__isnull=True)
    except ChatMessage.DoesNotExist:
        return Response({"detail": "Mensaje no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    msg.deleted_at = timezone.now()
    msg.save(update_fields=["deleted_at"])

    return Response({
        "ok": 1,
        "deleted_id": msg.id,
        "deleted_ts": int(msg.deleted_at.timestamp()),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_deleted_since(request, codigo: str):
    user = request.user
    codigo = (codigo or "").strip()
    if not _is_course_member(user, codigo):
        return _chat_forbidden()

    after_ts = int(request.query_params.get("after") or 0)
    # timestamp → aware datetime (UTC)
    after_dt = datetime.fromtimestamp(after_ts or 0, tz=dt_timezone.utc)

    # берём максимум 500 записей, отсортированных по времени удаления
    qs = ChatMessage.objects.filter(
        codigo=codigo,
        deleted_at__isnull=False,
        deleted_at__gt=after_dt,
    ).order_by("deleted_at")[:500]

    items = list(qs)                     # ← МАТЕРИАЛИЗУЕМ queryset
    ids = [m.id for m in items]
    last_ts = int(items[-1].deleted_at.timestamp()) if items else after_ts

    return Response({"deleted_ids": ids, "last_ts": last_ts})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_react_summary(request, codigo: str):
    user = request.user
    codigo = (codigo or "").strip()
    if not _is_course_member(user, codigo):
        return _chat_forbidden()

    ids_raw = request.query_params.get("ids")
    if isinstance(ids_raw, list):
        ids = [int(x) for x in ids_raw]
    else:
        ids = [int(x) for x in (ids_raw or "").split(",") if x]

    ids = list({i for i in ids if i > 0})
    ids = ids[:200]

    if not ids:
        return Response({"summary": {}})

    summary = {mid: [] for mid in ids}

    agg = (
        ChatReaction.objects
        .filter(msg_id__in=ids)
        .values("msg_id", "emoji")
        .annotate(cnt=Count("id"))
    )
    for r in agg:
        summary[r["msg_id"]].append(
            {"emoji": r["emoji"], "count": r["cnt"], "me": 0}
        )

    mine = ChatReaction.objects.filter(msg_id__in=ids, user=user)
    for r in mine:
        mid = r.msg_id
        emo = r.emoji
        lst = summary.get(mid)
        if lst is None:
            summary[mid] = [{"emoji": emo, "count": 1, "me": 1}]
            continue
        found = False
        for rec in lst:
            if rec["emoji"] == emo:
                rec["me"] = 1
                found = True
                break
        if not found:
            lst.append({"emoji": emo, "count": 1, "me": 1})

    for mid, lst in summary.items():
        summary[mid] = [
            rec for rec in lst
            if int(rec.get("count") or 0) > 0
        ]

    return Response({"summary": summary})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_teachers(request, codigo: str):
    user = request.user
    codigo = (codigo or "").strip()
    if not _is_course_member(user, codigo):
        return _chat_forbidden()

    qs = (
        Enrol.objects
        .select_related("user", "user__profile")
        .filter(codigo=codigo, role="teacher")
        .order_by("user_id")
    )

    out = []
    for e in qs:
        u = e.user
        prof = getattr(u, "profile", None)
        name = (getattr(prof, "display_name", "") or u.get_full_name() or u.email or u.username or "")
        out.append({"id": u.id, "name": name, "email": u.email or ""})

    return Response({"teachers": out})
 
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_dm_peers(request, codigo: str):
    user = request.user
    codigo = (codigo or "").strip()
    if not _is_course_member(user, codigo):
        return _chat_forbidden()

    me_is_teacher = bool(is_teacher(user))
    roles = ["student", "alumno"] if me_is_teacher else ["teacher"]

    qs = (
        Enrol.objects
        .select_related("user", "user__profile")
        .filter(codigo=codigo, role__in=roles)
        .exclude(user_id=user.id)
        .order_by("user_id")
    )

    logger.warning("dm_peers user=%s codigo=%s me_is_teacher=%s roles=%s count=%s",
                   user.id, codigo, me_is_teacher, roles, qs.count())
    logger.warning("dm_peers roles_in_course=%s",
                   list(Enrol.objects.filter(codigo=codigo).values_list("role", flat=True).distinct()))

    out = []
    for e in qs:
        u = e.user
        prof = getattr(u, "profile", None)
        name = (getattr(prof, "display_name", "") or u.get_full_name() or u.email or u.username or "")
        out.append({"id": u.id, "name": name, "email": u.email or ""})

    return Response({"peers": out, "mode": ("teacher" if me_is_teacher else "student")})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_dm_unread_map(request, codigo: str):
    user = request.user
    codigo = (codigo or "").strip()

    if not _is_course_member(user, codigo):
        return _chat_forbidden()

    me_is_teacher = is_teacher(user)

    # кого показываем в списке
    roles = ["student", "alumno"] if me_is_teacher else ["teacher"]

    peer_ids = list(
        Enrol.objects
        .filter(codigo=codigo, role__in=roles)
        .exclude(user_id=user.id)
        .values_list("user_id", flat=True)
        .distinct()
    )

    if not peer_ids:
        return Response({"map": {}})

    # последнее прочитанное по каждому peer
    reads = ChatRead.objects.filter(
        codigo=codigo,
        user=user,
        kind="dm",
        peer_user_id__in=peer_ids,
    ).values_list("peer_user_id", "last_msg_id")

    last_seen = {pid: mid for pid, mid in reads}

    out = {}

    for pid in peer_ids:
        seen = int(last_seen.get(pid, 0) or 0)

        # сообщения ОТ peer → МНЕ
        cnt = ChatMessage.objects.filter(
            codigo=codigo,
            kind="dm",
            deleted_at__isnull=True,
            user_id=pid,           # отправитель = peer
            to_user_id=user.id,    # получатель = я
            id__gt=seen,
        ).count()

        out[str(pid)] = cnt

    return Response({"map": out})
