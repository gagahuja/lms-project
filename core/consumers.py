import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.class_id = self.scope['url_route']['kwargs']['class_id']
        self.room_group_name = f'chat_{self.class_id}'

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

        if msg_type == "mute_user":
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
        else:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": data.get("message"),
                    "user": self.scope["user"].username,
                    "msg_type": "chat"
                }
            )
        


    async def mute_command(self, event):
        await self.send(text_data=json.dumps({
            "type": "mute_user",
            "target": event["target"]
        }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "user": event["user"],
            "type": event.get("msg_type", "chat")
        }))

    async def raise_hand_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "raise_hand",
            "user": event["user"]
        }))