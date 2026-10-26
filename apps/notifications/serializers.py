"""Serializers del módulo de notificaciones."""

from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "uuid",
            "title",
            "message",
            "category",
            "category_display",
            "priority",
            "priority_display",
            "link",
            "payload",
            "is_read",
            "read_at",
            "created_at",
        )
        read_only_fields = fields


class MarkReadSerializer(serializers.Serializer):
    uuids = serializers.ListField(child=serializers.UUIDField(), required=False)
    all = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if not attrs.get("all") and not attrs.get("uuids"):
            raise serializers.ValidationError("Indique 'uuids' o 'all=true'.")
        return attrs
