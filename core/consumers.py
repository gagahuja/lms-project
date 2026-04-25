import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        self.username = self.scope["user"].username  # ✅ ADD THIS

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

        if msg_type == "kick_user":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "kick_command",
                    "target": data.get("target"),
                }
            )
        elif msg_type == "mute_user":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "mute_command",
                    "target": data.get("target"),
                }
            )
        elif msg_type == "raise_hand":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "raise_hand_event",
                    "user": self.scope["user"].username,
                }
            )
        elif msg_type == "user_join":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_join_event",
                    "uid": data.get("uid"),
                    "username": data.get("username"),
                }
            )
        else:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": data.get("message"),
                    "user": self.username,
                }
            )
        


    async def mute_command(self, event):
        await self.send(text_data=json.dumps({
            "type": "mute_user",
            "target": event["target"]
        }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat",
            "message": event["message"],
            "user": event["user"],
        }))

    async def raise_hand_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "raise_hand",
            "user": event["user"]
        }))

    async def kick_command(self, event):
        await self.send(text_data=json.dumps({
            "type": "kick_user",
            "target": event["target"]
        }))

    async def user_join_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "user_join",
            "uid": event["uid"],
            "username": event["username"],
        }))