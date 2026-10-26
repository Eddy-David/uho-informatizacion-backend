"""Serializers del Solapín Digital."""

from __future__ import annotations

from rest_framework import serializers

from apps.usuarios.models import User
from apps.solapines.models import Badge, BadgePrintJob, BadgeTemplate


class BadgeTemplateSerializer(serializers.ModelSerializer):
    user_type_display = serializers.CharField(source="get_user_type_display", read_only=True)

    class Meta:
        model = BadgeTemplate
        fields = (
            "id",
            "uuid",
            "name",
            "user_type",
            "user_type_display",
            "campus",
            "background_image",
            "primary_color",
            "secondary_color",
            "zones",
            "is_default",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")

    def validate_zones(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Las zonas deben ser un objeto JSON.")
        allowed = {"photo", "qr", "name", "identity_card", "user_type", "access_level", "logo"}
        unknown = set(value) - allowed
        if unknown:
            raise serializers.ValidationError(
                f"Zonas no reconocidas: {', '.join(sorted(unknown))}. "
                f"Permitidas: {', '.join(sorted(allowed))}."
            )
        return value


class BadgeUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="nombre_completo", read_only=True)
    initials = serializers.CharField(read_only=True)
    identity_card = serializers.CharField(read_only=True)
    photo = serializers.ImageField(source="foto", read_only=True)
    user_type = serializers.CharField(source="tipo_usuario", read_only=True)
    campus = serializers.CharField(source="campus_sede", read_only=True)
    position = serializers.CharField(source="cargo", read_only=True)
    access_level = serializers.CharField(source="nivel_acceso", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "uuid",
            "username",
            "nombres",
            "apellidos",
            "nombre_completo",
            "full_name",
            "initials",
            "ci",
            "identity_card",
            "foto",
            "photo",
            "tipo_usuario",
            "user_type",
            "campus_sede",
            "campus",
            "area",
            "cargo",
            "position",
            "nivel_acceso",
            "access_level",
        )


class BadgeSerializer(serializers.ModelSerializer):
    user_detail = BadgeUserSerializer(source="user", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    access_level_display = serializers.CharField(source="get_access_level_display", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    qr_payload = serializers.CharField(read_only=True)
    qr_image_url = serializers.SerializerMethodField()

    def get_qr_image_url(self, obj) -> str:
        """URL del QR en PNG (sólo UUID + estado; RF-03.9)."""
        request = self.context.get("request")
        path = f"/solapines/badges/{obj.uuid}/qr/"
        return request.build_absolute_uri(path) if request else path

    class Meta:
        model = Badge
        fields = (
            "id",
            "uuid",
            "badge_number",
            "user",
            "user_detail",
            "template",
            "template_name",
            "access_level",
            "access_level_display",
            "status",
            "status_display",
            "qr_token",
            "codigo_qr",
            "qr_payload",
            "qr_image_url",
            "is_valid",
            "issued_at",
            "expires_at",
            "valid_from",
            "valid_until",
            "notes",
        )
        read_only_fields = (
            "id",
            "uuid",
            "badge_number",
            "qr_token",
            "codigo_qr",
            "qr_payload",
            "qr_image_url",
            "issued_at",
            "is_valid",
        )


class BadgeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = (
            "user",
            "template",
            "access_level",
            "expires_at",
            "valid_from",
            "valid_until",
            "notes",
        )

    def validate(self, attrs):
        user = attrs.get("user") or getattr(self.instance, "user", None)
        if (
            user
            and Badge.objects.filter(user=user, status=Badge.Status.ACTIVE)
            .exclude(pk=getattr(self.instance, "pk", None))
            .exists()
        ):
            raise serializers.ValidationError(
                {"user": "El usuario ya posee un solapín activo. Cancele o reemplace el existente."}
            )
        if attrs.get("valid_until") and attrs.get("valid_from"):
            if attrs["valid_until"] < attrs["valid_from"]:
                raise serializers.ValidationError(
                    {"valid_until": "La fecha final no puede ser anterior a la inicial."}
                )
        return attrs


class BadgeLevelUpdateSerializer(serializers.Serializer):
    access_level = serializers.ChoiceField(choices=Badge._meta.get_field("access_level").choices)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class BadgeCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, help_text="Motivo de la cancelación (RF-03.6).")


class BadgeVerifySerializer(serializers.Serializer):
    """Entrada de verificación: token QR o número de solapín/CI."""

    qr_token = serializers.CharField(required=False, allow_blank=True)
    identity_card = serializers.CharField(required=False, allow_blank=True)
    badge_number = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not any(attrs.get(k) for k in ("qr_token", "identity_card", "badge_number")):
            raise serializers.ValidationError("Proporcione qr_token, identity_card o badge_number.")
        return attrs


class BadgePrintJobSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = BadgePrintJob
        fields = (
            "id",
            "uuid",
            "campus",
            "area",
            "user_type",
            "total",
            "processed",
            "status",
            "status_display",
            "file",
            "error_message",
            "created_at",
        )
        read_only_fields = ("id", "uuid", "processed", "status", "file", "error_message", "total")
