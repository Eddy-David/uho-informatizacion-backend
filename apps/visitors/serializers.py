"""Serializers del módulo de visitantes."""

from __future__ import annotations

from rest_framework import serializers

from apps.visitors.models import Visitor, VisitRequest


class VisitRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source="requester.nombre_completo", read_only=True)
    reviewer_name = serializers.CharField(source="reviewer.nombre_completo", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    has_visitor = serializers.SerializerMethodField()

    class Meta:
        model = VisitRequest
        fields = (
            "id",
            "uuid",
            "code",
            "requester",
            "requester_name",
            "visitor_name",
            "visitor_identity_card",
            "visitor_phone",
            "visitor_organization",
            "reason",
            "area",
            "campus",
            "valid_from",
            "valid_until",
            "vehicle_plate",
            "status",
            "status_display",
            "reviewer",
            "reviewer_name",
            "reviewed_at",
            "review_comment",
            "attachments",
            "duration_days",
            "has_visitor",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "uuid",
            "code",
            "requester",
            "status",
            "reviewer",
            "reviewed_at",
            "review_comment",
            "created_at",
            "updated_at",
        )

    def get_has_visitor(self, obj) -> bool:
        return hasattr(obj, "visitor")

    def validate(self, attrs):
        valid_from = attrs.get("valid_from") or getattr(self.instance, "valid_from", None)
        valid_until = attrs.get("valid_until") or getattr(self.instance, "valid_until", None)
        if valid_from and valid_until and valid_until < valid_from:
            raise serializers.ValidationError(
                {"valid_until": "La fecha final debe ser igual o posterior a la inicial."}
            )
        ci = attrs.get("visitor_identity_card") or getattr(
            self.instance, "visitor_identity_card", ""
        )
        if ci and (not ci.isdigit() or len(ci) != 11):
            raise serializers.ValidationError(
                {"visitor_identity_card": "El CI debe tener exactamente 11 dígitos."}
            )
        return attrs


class VisitReviewSerializer(serializers.Serializer):
    """Decisión del aprobador sobre una solicitud."""

    action = serializers.ChoiceField(choices=("approve", "reject", "request_changes"))
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if attrs["action"] in ("reject", "request_changes") and not attrs.get("comment"):
            raise serializers.ValidationError(
                {"comment": "Debe indicar el motivo al rechazar o solicitar cambios."}
            )
        return attrs


class VisitorSerializer(serializers.ModelSerializer):
    request_code = serializers.CharField(source="visit_request.code", read_only=True)
    host_name = serializers.CharField(source="host_user.nombre_completo", read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Visitor
        fields = (
            "id",
            "uuid",
            "visit_request",
            "request_code",
            "user",
            "full_name",
            "identity_card",
            "phone",
            "organization",
            "host_user",
            "host_name",
            "campus",
            "area",
            "valid_from",
            "valid_until",
            "checked_in_at",
            "checked_out_at",
            "is_valid",
            "created_at",
        )
        read_only_fields = fields
