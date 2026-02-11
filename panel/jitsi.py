import time, jwt
from django.conf import settings

def build_jitsi_jwt(*, room: str, user_name: str, is_teacher: bool) -> str | None:
    if not (settings.JITSI_JWT_SECRET and is_teacher):
        return None

    now = int(time.time())
    payload = {
        "aud": settings.JITSI_JWT_AUD,
        "iss": settings.JITSI_JWT_APP_ID,
        "sub": settings.JITSI_DOMAIN,
        "room": room or "*",
        "iat": now,
        "exp": now + int(settings.JITSI_JWT_TTL_SECONDS),
        "context": {
            "user": {
                "name": user_name,
                "moderator": True,   # ✅ только учитель
            }
        }
    }
    return jwt.encode(payload, settings.JITSI_JWT_SECRET, algorithm="HS256")