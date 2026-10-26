"""Vistas del módulo (CRUD con RBAC y auditoría automática)."""

from rest_framework import permissions

from apps.usuarios.constants import Permission
from apps.usuarios.rbac import HasPerm, HasPermForWrite
from apps.core.mixins import AuditableModelViewSet  # noqa: F401 (documentación)
from apps.maintenance.models import Asset, WorkOrder
from apps.maintenance.serializers import AssetSerializer, WorkOrderSerializer


class AssetViewSet(AuditableModelViewSet):
    """CRUD de Asset."""

    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.MAINTENANCE_VIEW)]
    search_fields = ["code", "name", "location"]
    ordering_fields = ["created_at"]
    filterset_fields = ["status"]


class WorkOrderViewSet(AuditableModelViewSet):
    """CRUD de WorkOrder."""

    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasPermForWrite(Permission.MAINTENANCE_MANAGE, Permission.MAINTENANCE_VIEW),
    ]
    search_fields = ["title"]
    ordering_fields = ["created_at"]
    filterset_fields = ["status"]
