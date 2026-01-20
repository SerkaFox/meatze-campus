from functools import wraps
from django.http import JsonResponse
from django.conf import settings

def require_admin_token(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        token = request.GET.get("adm") or request.headers.get("X-MZ-Admin")
        expected = getattr(settings, "MEATZE_ADMIN_PASS", "MeatzeIT")
        if token != expected:
            return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped
