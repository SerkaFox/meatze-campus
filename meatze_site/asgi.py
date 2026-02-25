import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

import panel.shortshare.routing  # <-- важно

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meatze_site.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(panel.shortshare.routing.websocket_urlpatterns)
    ),
})