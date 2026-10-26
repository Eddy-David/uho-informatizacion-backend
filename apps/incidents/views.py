"""Vistas del módulo de incidencias."""

from __future__ import annotations

from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import AuditableModelViewSet
from apps.core.permissions import IsAccessOperator
from apps.incidents.models import Incident, IncidentFollowUp
from apps.incidents.serializers import (
    IncidentFollowUpSerializer,
    IncidentSerializer,
    IncidentStatusSerializer,
)
from apps.notifications.services import notify_security_team


class IncidentViewSet(AuditableModelViewSet):
    """Registro y seguimiento de incidencias."""

    queryset = Incident.objects.select_related("reported_by", "assigned_to").prefetch_related(
        "follow_ups"
    )
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]
    filterset_fields = ["status", "severity", "campus", "incident_type"]
    search_fields = ["title", "person_name", "person_identity_card", "code"]
    ordering_fields = ["occurred_at", "severity", "status"]
    lookup_field = "uuid"

    def perform_create(self, serializer):
        incident = serializer.save(reported_by=self.request.user, created_by=self.request.user)
        if incident.severity in (Incident.Severity.HIGH, Incident.Severity.CRITICAL):
            notify_security_team(
                title="Incidencia de alta gravedad",
                message=f"{incident.code}: {incident.title}",
                link=f"/incidents/{incident.uuid}",
                payload={"incident": str(incident.uuid), "severity": incident.severity},
            )

    @extend_schema(summary="Cambiar estado / agregar seguimiento", tags=["Incidencias"])
    @action(detail=True, methods=["post"], url_path="status")
    def change_status(self, request, uuid=None):
        incident = self.get_object()
        serializer = IncidentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        incident.status = data["status"]
        if data.get("resolution"):
            incident.resolution = data["resolution"]
        incident.updated_by = request.user
        incident.save()

        if data.get("comment"):
            IncidentFollowUp.objects.create(
                incident=incident,
                author=request.user,
                comment=data["comment"],
                new_status=data["status"],
            )
        return Response(IncidentSerializer(incident).data)

    @extend_schema(summary="Estadísticas de incidencias", tags=["Incidencias"])
    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = self.filter_queryset(self.get_queryset())
        return Response(
            {
                "total": qs.count(),
                "by_status": {
                    key: value
                    for key, value in qs.values_list("status").annotate(total=Count("id"))
                },
                "by_severity": {
                    key: value
                    for key, value in qs.values_list("severity").annotate(total=Count("id"))
                },
                "by_campus": {
                    key or "SIN_SEDE": value
                    for key, value in qs.values_list("campus").annotate(total=Count("id"))
                },
            }
        )


class IncidentFollowUpViewSet(viewsets.ModelViewSet):
    """Comentarios y seguimiento de incidencias."""

    queryset = IncidentFollowUp.objects.select_related("author")
    serializer_class = IncidentFollowUpSerializer
    permission_classes = [permissions.IsAuthenticated, IsAccessOperator]
    lookup_field = "uuid"

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
