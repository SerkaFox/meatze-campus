# panel/decorators.py (или где удобно)
from functools import wraps
from urllib.parse import urlencode
from django.shortcuts import redirect

try:
    from api.models import UserProfile
except ImportError:
    UserProfile = None

def require_profile_complete(view):
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_authenticated and UserProfile is not None:
            p = getattr(request.user, "profile", None) or UserProfile.objects.filter(user=request.user).first()
            # если профиля нет — тоже считаем “не заполнено”
            if (not p) or (not p.is_complete()):
                nxt = request.get_full_path()
                qs = urlencode({"tab": "profile", "next": nxt})
                return redirect(f"/acceder/?{qs}")
        return view(request, *args, **kwargs)
    return _wrapped
