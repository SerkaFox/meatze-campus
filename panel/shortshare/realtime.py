from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def group_name(code: str) -> str:
    return f"shortshare_{code}"

def push(code: str, payload: dict):
    layer = get_channel_layer()
    if not layer:
        return
    async_to_sync(layer.group_send)(
        group_name(code),
        {"type": "broadcast", "payload": payload},
    )