import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

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

        # 💬 CHAT
        if msg_type == "chat":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": data.get("message"),
                    "user": self.username,
                }
            )

        # ❌ KICK USER
        elif msg_type == "kick_user":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "kick_command",
                    "target": str(data.get("target")),
                }
            )

        # 👤 USER JOIN (for name mapping)
        elif msg_type == "user_join":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_join_event",
                    "uid": str(data.get("uid")),
                    "username": data.get("username"),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat",
            "message": event["message"],
            "user": event["user"],
        }))

    async def kick_command(self, event):
        await self.send(text_data=json.dumps({
            "type": "kick_user",
            "target": event["target"],
        }))

    async def user_join_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "user_join",
            "uid": event["uid"],
            "username": event["username"],
        }))