"""Vistas del módulo (CRUD con RBAC y auditoría automática)."""

from rest_framework import permissions

from apps.usuarios.constants import Permission
from apps.usuarios.rbac import HasPerm, HasPermForWrite
from apps.core.mixins import AuditableModelViewSet  # noqa: F401 (documentación)
from apps.hr.models import EmployeeRecord, LeaveRequest, Position
from apps.hr.serializers import EmployeeRecordSerializer, LeaveRequestSerializer, PositionSerializer


class PositionViewSet(AuditableModelViewSet):
    """CRUD de Position."""

    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.HR_VIEW)]
    search_fields = ["code", "name"]
    ordering_fields = ["created_at"]
    filterset_fields = []


class EmployeeRecordViewSet(AuditableModelViewSet):
    """CRUD de EmployeeRecord."""

    queryset = EmployeeRecord.objects.all()
    serializer_class = EmployeeRecordSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasPermForWrite(Permission.HR_MANAGE, Permission.HR_VIEW),
    ]
    search_fields = ["employee_number", "department"]
    ordering_fields = ["created_at"]
    filterset_fields = ["status"]


class LeaveRequestViewSet(AuditableModelViewSet):
    """CRUD de LeaveRequest."""

    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.HR_VIEW)]
    search_fields = ["employee__employee_number"]
    ordering_fields = ["created_at"]
    filterset_fields = ["status"]
