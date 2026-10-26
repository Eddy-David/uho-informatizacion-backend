"""Serializers del módulo."""

from rest_framework import serializers

from apps.maintenance.models import Asset, WorkOrder


class AssetSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = Asset
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class WorkOrderSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = WorkOrder
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
