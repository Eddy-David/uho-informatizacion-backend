"""Consumers de WebSockets para las notificaciones en tiempo real."""

from __future__ import annotations

import json
from urllib.parse import unquote

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.notifications.models import Notification
from apps.notifications.services import broadcast_group_name, user_group_name


class NotificationConsumer(AsyncWebsocketConsumer):
    """``ws://host/ws/notifications/?token=<JWT>``

    El token JWT se valida en el handshake; si es válido, el usuario se une a
    su grupo personal y al grupo de seguridad (si su rol lo permite).
    """

    async def connect(self):
        self.user = await self._get_user()
        if self.user is None:
            await self.close(code=4401)
            return

        self.user_group = user_group_name(self.user.pk)
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        self.security_group = None
        if await self._is_security():
            self.security_group = broadcast_group_name("security")
            await self.channel_layer.group_add(self.security_group, self.channel_name)

        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection.ready",
                    "user": self.user.username,
                    "unread": await self._unread_count(),
                },
                ensure_ascii=False,
            )
        )

    async def disconnect(self, close_code):
        if getattr(self, "user", None) is None:
            return
        await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if self.security_group:
            await self.channel_layer.group_discard(self.security_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Comandos del cliente: ``ping`` y ``mark_read``."""
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            return
        action = data.get("action")
        if action == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
        elif action == "mark_read":
            uuid = data.get("uuid")
            if uuid:
                await self._mark_read(uuid)
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "notification.read",
                            "uuid": uuid,
                            "unread": await self._unread_count(),
                        }
                    )
                )

    # --- Handlers de eventos de grupo -------------------------------------
    async def notification_message(self, event):
        """Reenvía al cliente cualquier evento publicado en el grupo."""
        await self.send(text_data=json.dumps(event["payload"], ensure_ascii=False, default=str))

    # --- Helpers -----------------------------------------------------------
    async def _get_user(self):
        token = self._query_param("token")
        if not token:
            return None
        return await self._authenticate(token)

    @database_sync_to_async
    def _authenticate(self, token: str):
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import AccessToken

        from apps.usuarios.models import User

        try:
            validated = AccessToken(token)
        except TokenError:
            return None
        return User.objects.filter(pk=validated["user_id"], estado=True).first()

    @database_sync_to_async
    def _is_security(self) -> bool:
        from apps.core.constants import Role

        return self.user.is_superuser or self.user.role in (
            Role.SUPERADMIN,
            Role.ADMIN,
            Role.SECURITY_DIRECTOR,
            Role.SECURITY_OFFICER,
        )

    @database_sync_to_async
    def _unread_count(self) -> int:
        return Notification.objects.filter(user=self.user, is_read=False).count()

    @database_sync_to_async
    def _mark_read(self, uuid: str) -> None:
        Notification.objects.filter(user=self.user, uuid=uuid, is_read=False).update(is_read=True)

    def _query_param(self, key: str):
        query = self.scope.get("query_string", b"").decode()
        for part in query.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                if k == key:
                    return unquote(v)
        return None
