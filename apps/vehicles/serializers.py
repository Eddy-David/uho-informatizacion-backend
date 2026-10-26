"""Serializers del módulo de vehículos."""

from __future__ import annotations

from rest_framework import serializers

from apps.core.constants import MovementType
from apps.vehicles.models import AuthorizedVehicle, VehicleMovement


class AuthorizedVehicleSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = AuthorizedVehicle
        fields = (
            "id",
            "uuid",
            "plate",
            "vehicle_type",
            "brand",
            "model",
            "color",
            "owner_name",
            "owner_identity_card",
            "campus",
            "authorization_reason",
            "valid_from",
            "valid_until",
            "is_active",
            "is_valid",
            "approved_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "uuid", "approved_by", "created_at", "updated_at")

    def validate_plate(self, value):
        value = value.strip().upper()
        if len(value) < 4:
            raise serializers.ValidationError("La placa debe tener al menos 4 caracteres.")
        return value

    def validate(self, attrs):
        valid_from = attrs.get("valid_from") or getattr(self.instance, "valid_from", None)
        valid_until = attrs.get("valid_until") or getattr(self.instance, "valid_until", None)
        if valid_from and valid_until and valid_until < valid_from:
            raise serializers.ValidationError(
                {"valid_until": "La vigencia final no puede ser anterior a la inicial."}
            )
        return attrs


class VehicleMovementSerializer(serializers.ModelSerializer):
    registered_by_name = serializers.CharField(source="registered_by.nombre_completo", read_only=True)
    status_after_display = serializers.CharField(source="get_status_after_display", read_only=True)

    class Meta:
        model = VehicleMovement
        fields = (
            "id",
            "uuid",
            "vehicle",
            "plate",
            "vehicle_type",
            "driver_name",
            "driver_identity_card",
            "campus",
            "access_point",
            "movement",
            "authorized",
            "is_exception",
            "reason",
            "status_after",
            "status_after_display",
            "registered_by",
            "registered_by_name",
            "occurred_at",
        )
        read_only_fields = (
            "id",
            "uuid",
            "vehicle",
            "authorized",
            "is_exception",
            "status_after",
            "registered_by",
            "occurred_at",
        )


class VehicleCheckSerializer(serializers.Serializer):
    """```GET /vehicles/check/?plate=H123456``` verifica el catálogo."""

    plate = serializers.CharField()
    campus = serializers.CharField(required=False, allow_blank=True)


class RegisterMovementSerializer(serializers.Serializer):
    plate = serializers.CharField()
    movement = serializers.ChoiceField(choices=MovementType.choices, default=MovementType.ENTRY)
    vehicle_type = serializers.CharField(required=False, allow_blank=True)
    driver_name = serializers.CharField(required=False, allow_blank=True)
    driver_identity_card = serializers.CharField(required=False, allow_blank=True, max_length=11)
    campus = serializers.CharField(required=False, allow_blank=True)
    access_point = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
