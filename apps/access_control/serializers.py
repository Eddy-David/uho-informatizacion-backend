"""Serializers del control de acceso."""

from __future__ import annotations

from rest_framework import serializers

from apps.access_control.models import AccessLog
from apps.core.constants import MovementType
from apps.solapines.serializers import BadgeSerializer


class AccessLogSerializer(serializers.ModelSerializer):
    registered_by_name = serializers.CharField(source="registered_by.nombre_completo", read_only=True)
    access_point_name = serializers.CharField(source="access_point.name", read_only=True)
    movement_display = serializers.CharField(source="get_movement_display", read_only=True)
    result_display = serializers.CharField(source="get_result_display", read_only=True)

    class Meta:
        model = AccessLog
        fields = (
            "id",
            "uuid",
            "occurred_at",
            "full_name",
            "identity_card",
            "user_type",
            "access_level",
            "user",
            "badge",
            "campus",
            "sede",
            "access_point",
            "access_point_name",
            "movement",
            "movement_display",
            "result",
            "result_display",
            "denial_reason",
            "channel",
            "observed",
            "registered_by",
            "registered_by_name",
            "synced_at",
            "client_uuid",
        )
        read_only_fields = fields  # la bitácora es inmutable vía API


class AccessVerificationRequestSerializer(serializers.Serializer):
    """Solicitud de verificación desde la web o la PWA."""

    qr_token = serializers.CharField(required=False, allow_blank=True)
    badge_number = serializers.CharField(required=False, allow_blank=True)
    identity_card = serializers.CharField(required=False, allow_blank=True)
    movement = serializers.ChoiceField(choices=MovementType.choices, default=MovementType.ENTRY)
    campus = serializers.CharField(required=False, allow_blank=True)
    access_point = serializers.UUIDField(required=False, allow_null=True)
    channel = serializers.ChoiceField(
        choices=AccessLog.Channel.choices, default=AccessLog.Channel.WEB
    )
    observed = serializers.CharField(required=False, allow_blank=True, max_length=255)
    device_info = serializers.CharField(required=False, allow_blank=True, max_length=200)
    client_uuid = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if not any(attrs.get(k) for k in ("qr_token", "badge_number", "identity_card")):
            raise serializers.ValidationError(
                "Debe proporcionar qr_token, badge_number o identity_card."
            )
        return attrs


class AccessVerificationResponseSerializer(serializers.Serializer):
    allowed = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField()
    badge = BadgeSerializer(required=False, allow_null=True)
    log = AccessLogSerializer(required=False, allow_null=True)


class AccessVerifySerializer(serializers.Serializer):
    """``{"identificador": "<UUID del QR> o <CI>"}`` (RF-04.1 / RF-04.2)."""

    identificador = serializers.CharField(max_length=200)

    def validate_identificador(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Indique el UUID del QR o el carné de identidad.")
        return value.strip()


class AccessVerifyResultSerializer(serializers.Serializer):
    permitido = serializers.BooleanField()
    razon = serializers.CharField()
    mensaje = serializers.CharField()
    datos_persona = serializers.DictField()
    solapin = serializers.DictField(required=False, allow_null=True)


class AccessRegisterSerializer(serializers.Serializer):
    """Registro manual de un movimiento desde el punto de control (RF-04.5)."""

    solapin = serializers.UUIDField(help_text="codigo_qr (o uuid) del solapín.")
    tipo_movimiento = serializers.ChoiceField(
        choices=MovementType.choices, default=MovementType.ENTRY
    )
    sede = serializers.UUIDField(
        required=False, allow_null=True, help_text="UUID de la sede del nomenclador."
    )
    punto_control = serializers.UUIDField(required=False, allow_null=True)
    canal = serializers.ChoiceField(
        choices=AccessLog.Channel.choices, required=False, allow_blank=True
    )
    observaciones = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AccessStatsSerializer(serializers.Serializer):
    date = serializers.DateField()
    total = serializers.IntegerField()
    granted = serializers.IntegerField()
    denied = serializers.IntegerField()
    by_campus = serializers.DictField(child=serializers.IntegerField())
    by_hour = serializers.DictField(child=serializers.IntegerField())
    by_user_type = serializers.DictField(child=serializers.IntegerField())


class SyncAccessLogItemSerializer(AccessVerificationRequestSerializer):
    """Elemento de la cola offline de la PWA (RNF-09)."""

    occurred_at = serializers.DateTimeField()
    client_uuid = serializers.UUIDField()
