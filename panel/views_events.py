# panel/views_events.py
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from api.utils_events import log_event

@csrf_exempt  # если хочешь без CSRF; см. ниже как сделать правильно без exempt
@login_required
@require_http_methods(["POST"])
def log_learning_event_panel(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        data = {}

    ev = (data.get("event") or "").strip()[:50]
    if not ev:
        return JsonResponse({"ok": False, "error": "event_required"}, status=400)

    curso_codigo = (data.get("curso_codigo") or "").strip()[:32]
    session_id   = (data.get("session_id") or "").strip()[:64]

    seq = data.get("seq")
    try:
        seq = int(seq) if seq is not None else None
    except Exception:
        seq = None

    obj_type = (data.get("object_type") or "").strip()[:50]
    obj_id   = (data.get("object_id") or "").strip()[:64]
    page     = (data.get("page") or "").strip()[:200]
    ref      = (data.get("ref") or "").strip()[:200]
    meta     = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    ts       = data.get("ts")

    e = log_event(
        request,
        event=ev,
        curso_codigo=curso_codigo,
        object_type=obj_type,
        object_id=obj_id,
        meta=meta,
        session_id=session_id,
        seq=seq,
        page=page,
        ref=ref,
        client_ts=ts,
    )

    return JsonResponse({"ok": True, "id": (e.id if e else None)})
