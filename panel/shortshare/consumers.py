import json
from channels.generic.websocket import AsyncWebsocketConsumer

def group_name(code: str) -> str:
    return f"shortshare_{code}"

class ShortShareRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"]
        self.group = group_name(self.code)

        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        # опционально: пинг что подключились
        await self.send(text_data=json.dumps({"type": "hello", "code": self.code}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    # мы не принимаем команды от клиента — только пушим события
    async def receive(self, text_data=None, bytes_data=None):
        return

    # handler для group_send
    async def broadcast(self, event):
        # event["payload"] должен быть JSON-serializable
        await self.send(text_data=json.dumps(event["payload"]))