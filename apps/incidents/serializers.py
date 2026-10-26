"""Serializers del módulo de incidencias."""

from __future__ import annotations

from rest_framework import serializers

from apps.incidents.models import Incident, IncidentFollowUp


class IncidentFollowUpSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.nombre_completo", read_only=True)

    class Meta:
        model = IncidentFollowUp
        fields = (
            "id",
            "uuid",
            "incident",
            "author",
            "author_name",
            "comment",
            "new_status",
            "created_at",
        )
        read_only_fields = ("id", "uuid", "incident", "author", "created_at")


class IncidentSerializer(serializers.ModelSerializer):
    reported_by_name = serializers.CharField(source="reported_by.nombre_completo", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.nombre_completo", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    follow_ups = IncidentFollowUpSerializer(many=True, read_only=True)

    class Meta:
        model = Incident
        fields = (
            "id",
            "uuid",
            "code",
            "title",
            "description",
            "incident_type",
            "severity",
            "severity_display",
            "status",
            "status_display",
            "campus",
            "access_point",
            "access_log",
            "visit_request",
            "vehicle_movement",
            "person_name",
            "person_identity_card",
            "photo",
            "reported_by",
            "reported_by_name",
            "assigned_to",
            "assigned_to_name",
            "occurred_at",
            "closed_at",
            "resolution",
            "follow_ups",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "uuid",
            "code",
            "reported_by",
            "closed_at",
            "created_at",
            "updated_at",
        )


class IncidentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Incident.Status.choices)
    resolution = serializers.CharField(required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)
