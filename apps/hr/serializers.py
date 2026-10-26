"""Serializers del módulo."""

from rest_framework import serializers

from apps.hr.models import EmployeeRecord, LeaveRequest, Position


class PositionSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = Position
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class EmployeeRecordSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = EmployeeRecord
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
