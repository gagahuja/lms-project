import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Attendance
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        self.username = self.scope["user"].username if self.scope["user"].is_authenticated else "Guest"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # 🔥 CREATE ATTENDANCE ENTRY
        user = self.scope.get("user")

        if user and not isinstance(user, AnonymousUser):

            self.attendance = await sync_to_async(Attendance.objects.create)(
                user=user,
                room=self.room_name
            )

        print(f"✅ {self.username} connected to {self.room_group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):

            # 🔥 MARK LEAVE TIME
            if hasattr(self, "attendance"):
                await sync_to_async(self._safe_leave)()

            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)

        msg_type = data.get("type")

        if msg_type == "chat":
            message = data.get("message", "").strip()

            if message:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": message,
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

        elif msg_type == "end_class":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "end_class_event"}
            )

        elif msg_type == "mic_status":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "mic_status_event",
                    "uid": str(data.get("uid")),
                    "status": data.get("status"),
                }
            )

        elif msg_type == "raise_hand":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "raise_hand_event",
                    "uid": str(data.get("uid")),
                    "username": data.get("username"),
                    "action": data.get("action")  # "raise" or "lower"
                }
            )

        elif msg_type == "reaction":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "reaction_event",
                    "uid": str(data.get("uid")),
                    "emoji": data.get("emoji"),
                }
            )

        elif msg_type == "spotlight":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "spotlight_event",
                    "uid": str(data.get("uid")),
                    "action": data.get("action")  # "on" or "off"
                }
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

    async def mic_status_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "mic_status",
            "uid": event["uid"],
            "status": event["status"]
        }))

    async def raise_hand_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "raise_hand",
            "uid": event["uid"],
            "username": event["username"],
            "action": event["action"]
        }))

    async def reaction_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "reaction",
            "uid": event["uid"],
            "emoji": event["emoji"]
        }))

    async def spotlight_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "spotlight",
            "uid": event["uid"],
            "action": event["action"]
        }))

    def _mark_leave(self):
        self.attendance.leave_time = timezone.now()
        self.attendance.save()

    def _safe_leave(self):
        if self.attendance:
            from django.utils import timezone
            self.attendance.leave_time = timezone.now()
            self.attendance.save()