"""Servicio de notificaciones: persistencia + difusión por WebSocket."""

from __future__ import annotations

import logging
from typing import Iterable

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from apps.notifications.models import Notification

logger = logging.getLogger("apps.notifications")
User = get_user_model()


def user_group_name(user_id) -> str:
    return f"notifications.user.{user_id}"


def broadcast_group_name(name: str) -> str:
    return f"notifications.group.{name}"


def _publish(group: str, event: dict) -> None:
    """Envía un evento al grupo de Channels (silencioso si Redis no responde)."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            group,
            {"type": "notification.message", "payload": event},
        )
    except Exception:  # pragma: no cover - Redis caído no debe romper la petición
        logger.warning("No se pudo difundir la notificación por WebSocket (grupo=%s)", group)


def notify_user(
    user,
    *,
    title: str,
    message: str,
    category: str = Notification.Category.SYSTEM,
    priority: str = Notification.Priority.NORMAL,
    link: str = "",
    payload: dict | None = None,
    send_email: bool = False,
) -> Notification:
    """Crea la notificación y la envía en tiempo real al usuario."""
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        category=category,
        priority=priority,
        link=link,
        payload=payload or {},
    )
    _publish(
        user_group_name(user.pk),
        {
            "type": "notification.created",
            "notification": {
                "uuid": str(notification.uuid),
                "title": notification.title,
                "message": notification.message,
                "category": notification.category,
                "priority": notification.priority,
                "link": notification.link,
                "created_at": notification.created_at.isoformat(),
                "is_read": False,
            },
        },
    )
    if send_email:
        from django.core.mail import send_mail

        try:
            send_mail(title, message, None, [user.email], fail_silently=True)
        except Exception:  # pragma: no cover
            logger.warning("No se pudo enviar el correo de notificación a %s", user.email)
    return notification


def notify_many(users: Iterable, **kwargs) -> int:
    """Notifica a varios usuarios; devuelve cuántos se notificaron."""
    count = 0
    for user in users:
        notify_user(user, **kwargs)
        count += 1
    return count


def notify_security_team(*, title: str, message: str, link: str = "", payload: dict | None = None):
    """Alerta a todo el personal de seguridad conectado (RF-10.1)."""
    from apps.core.constants import Role

    users = User.objects.filter(
        estado=True,
        role__in=(Role.SECURITY_DIRECTOR, Role.SECURITY_OFFICER, Role.ADMIN, Role.SUPERADMIN),
    )
    notify_many(
        users,
        title=title,
        message=message,
        category=Notification.Category.SECURITY,
        priority=Notification.Priority.HIGH,
        link=link,
        payload=payload,
    )
    _publish(
        broadcast_group_name("security"),
        {"type": "security.alert", "title": title, "message": message, "link": link},
    )


def notify_admins(*, title: str, message: str, link: str = "", payload: dict | None = None):
    from apps.core.constants import Role

    users = User.objects.filter(estado=True, role__in=(Role.ADMIN, Role.SUPERADMIN))
    return notify_many(
        users,
        title=title,
        message=message,
        category=Notification.Category.SYSTEM,
        link=link,
        payload=payload,
    )
