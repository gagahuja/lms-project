import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'room_{self.room_name}'
        self.username = self.scope["user"].username

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "chat":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": data.get("message"),
                    "user": self.username,
                }
            )

        elif msg_type == "kick":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "kick_user",
                    "target": str(data.get("target"))
                }
            )

        elif msg_type == "mute_all":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "mute_all_event"}
            )

        elif msg_type == "draw":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "draw_event",
                    "x": data.get("x"),
                    "y": data.get("y")
                }
            )

        elif msg_type == "end_class":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "end_class_event"}
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat",
            "user": event["user"],
            "message": event["message"]
        }))

    async def kick_user(self, event):
        await self.send(text_data=json.dumps({
            "type": "kick",
            "target": event["target"]
        }))

    async def mute_all_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "mute_all"
        }))

    async def end_class_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "end_class"
        }))

    async def draw_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "draw",
            "x": event["x"],
            "y": event["y"]
        }))