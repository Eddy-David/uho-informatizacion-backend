"""Vistas del módulo de notificaciones."""

from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.serializers import MarkReadSerializer, NotificationSerializer


class NotificationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Bandeja de notificaciones del usuario autenticado."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["is_read", "category", "priority"]
    ordering_fields = ["created_at"]
    lookup_field = "uuid"

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @extend_schema(summary="Contador de no leídas", tags=["Notificaciones"])
    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(is_read=False).count()})

    @extend_schema(
        summary="Marcar como leídas", request=MarkReadSerializer, tags=["Notificaciones"]
    )
    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request):
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qs = self.get_queryset().filter(is_read=False)
        if not serializer.validated_data.get("all"):
            qs = qs.filter(uuid__in=serializer.validated_data["uuids"])
        updated = qs.update(is_read=True, read_at=timezone.now())
        return Response({"updated": updated})
