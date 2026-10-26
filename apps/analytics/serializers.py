"""Serializers del módulo."""

from rest_framework import serializers

from apps.analytics.models import DashboardDefinition, KpiDefinition


class DashboardDefinitionSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = DashboardDefinition
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class KpiDefinitionSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = KpiDefinition
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
