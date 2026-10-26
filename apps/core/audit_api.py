"""API de consulta de la auditoría (solo lectura + exportación)."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.constants import Permission
from apps.usuarios.rbac import HasPerm
from apps.core.audit import AuditEvent
from apps.core.exports import export_to_excel, export_to_pdf


class AuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.nombre_completo", read_only=True)

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "created_at",
            "action",
            "severity",
            "module",
            "description",
            "actor",
            "actor_name",
            "actor_username",
            "actor_role",
            "target_type",
            "target_id",
            "target_repr",
            "changes",
            "metadata",
            "ip_address",
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
        )
        read_only_fields = fields


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Eventos de auditoría: consulta inmutable por filtros."""

    queryset = AuditEvent.objects.select_related("actor")
    serializer_class = AuditEventSerializer
    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.AUDIT_VIEW)]
    filterset_fields = ["action", "severity", "module", "actor"]
    search_fields = ["description", "actor_username", "target_repr", "target_id", "ip_address"]
    ordering_fields = ["created_at", "action", "module"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        date_from = parse_date(params.get("date_from", ""))
        date_to = parse_date(params.get("date_to", ""))
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    @extend_schema(summary="Resumen de auditoría (últimos 30 días)", tags=["Auditoría"])
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        since = timezone.now() - timedelta(days=30)
        qs = AuditEvent.objects.filter(created_at__gte=since)

        def group(field):
            return {
                item[field] or "—": item["total"]
                for item in qs.values(field).annotate(total=Count("id"))
            }

        return Response(
            {
                "period_days": 30,
                "total": qs.count(),
                "by_action": group("action"),
                "by_module": group("module"),
                "by_severity": group("severity"),
                "failed_logins": qs.filter(action=AuditEvent.Action.LOGIN_FAILED).count(),
                "critical": qs.filter(severity=AuditEvent.Severity.CRITICAL).count(),
                "top_actors": list(
                    qs.exclude(actor_username="")
                    .values("actor_username")
                    .annotate(total=Count("id"))
                    .order_by("-total")[:10]
                ),
            }
        )

    @extend_schema(
        summary="Exportar auditoría a Excel",
        parameters=[OpenApiParameter("date_from", str), OpenApiParameter("date_to", str)],
        tags=["Auditoría"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="export/excel",
        permission_classes=[permissions.IsAuthenticated, HasPerm(Permission.AUDIT_EXPORT)],
    )
    def export_excel(self, request):
        events = self.filter_queryset(self.get_queryset())[:20000]
        return export_to_excel(
            title="Auditoría del sistema",
            sheet_name="Auditoría",
            headers=[
                "Fecha",
                "Acción",
                "Módulo",
                "Actor",
                "Rol",
                "Objeto",
                "Descripción",
                "IP",
                "Estado",
            ],
            rows=[
                (
                    timezone.localtime(event.created_at).replace(tzinfo=None),
                    event.get_action_display(),
                    event.module,
                    event.actor_username or "sistema",
                    event.actor_role,
                    event.target_repr or event.target_id,
                    event.description,
                    event.ip_address or "",
                    event.status_code or "",
                )
                for event in events
            ],
            metadata={"Registros exportados": len(events)},
        )

    @extend_schema(
        summary="Exportar auditoría a PDF",
        parameters=[OpenApiParameter("date_from", str), OpenApiParameter("date_to", str)],
        tags=["Auditoría"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="export/pdf",
        permission_classes=[permissions.IsAuthenticated, HasPerm(Permission.AUDIT_EXPORT)],
    )
    def export_pdf(self, request):
        events = self.filter_queryset(self.get_queryset())[:2000]
        return export_to_pdf(
            title="Auditoría del sistema",
            context={
                "headers": ["Fecha", "Acción", "Módulo", "Actor", "Objeto", "IP"],
                "rows": [
                    [
                        timezone.localtime(event.created_at).strftime("%Y-%m-%d %H:%M"),
                        event.get_action_display(),
                        event.module,
                        event.actor_username or "sistema",
                        event.target_repr or event.target_id,
                        event.ip_address or "",
                    ]
                    for event in events
                ],
                "filters": {k: v for k, v in request.query_params.items()},
            },
        )


class PermissionMatrixView(APIView):
    """``GET /api/v1/audit/permissions/`` — catálogo de permisos agrupado."""

    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.AUDIT_VIEW)]

    @extend_schema(summary="Catálogo de permisos por recurso", tags=["Auditoría"])
    def get(self, request):
        from apps.usuarios.rbac import permissions_by_module

        return Response(permissions_by_module())
