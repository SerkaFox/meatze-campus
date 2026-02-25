from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/shortshare/(?P<code>\d{2,4})/$", consumers.ShortShareRoomConsumer.as_asgi()),
]