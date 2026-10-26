"""Vistas del módulo (CRUD con RBAC y auditoría automática)."""

from rest_framework import permissions

from apps.usuarios.constants import Permission
from apps.usuarios.rbac import HasPerm, HasPermForWrite
from apps.analytics.models import DashboardDefinition, KpiDefinition
from apps.analytics.serializers import DashboardDefinitionSerializer, KpiDefinitionSerializer
from apps.core.mixins import AuditableModelViewSet  # noqa: F401 (documentación)


class DashboardDefinitionViewSet(AuditableModelViewSet):
    """CRUD de DashboardDefinition."""

    queryset = DashboardDefinition.objects.all()
    serializer_class = DashboardDefinitionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasPermForWrite(Permission.ANALYTICS_MANAGE, Permission.ANALYTICS_VIEW),
    ]
    search_fields = ["slug", "title"]
    ordering_fields = ["created_at"]
    filterset_fields = ["is_public"]


class KpiDefinitionViewSet(AuditableModelViewSet):
    """CRUD de KpiDefinition."""

    queryset = KpiDefinition.objects.all()
    serializer_class = KpiDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.ANALYTICS_VIEW)]
    search_fields = ["code", "label"]
    ordering_fields = ["created_at"]
    filterset_fields = []
