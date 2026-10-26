"""Vistas del módulo (CRUD con RBAC y auditoría automática)."""

from rest_framework import permissions

from apps.academic.models import AcademicPeriod, Course, GradeRecord
from apps.academic.serializers import (
    AcademicPeriodSerializer,
    CourseSerializer,
    GradeRecordSerializer,
)
from apps.usuarios.constants import Permission
from apps.usuarios.rbac import HasPerm, HasPermForWrite
from apps.core.mixins import AuditableModelViewSet  # noqa: F401 (documentación)


class AcademicPeriodViewSet(AuditableModelViewSet):
    """CRUD de AcademicPeriod."""

    queryset = AcademicPeriod.objects.all()
    serializer_class = AcademicPeriodSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasPermForWrite(Permission.ACADEMIC_MANAGE, Permission.ACADEMIC_VIEW),
    ]
    search_fields = ["code", "name"]
    ordering_fields = ["created_at"]
    filterset_fields = ["kind", "is_active"]


class CourseViewSet(AuditableModelViewSet):
    """CRUD de Course."""

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.ACADEMIC_VIEW)]
    search_fields = ["code", "name"]
    ordering_fields = ["created_at"]
    filterset_fields = []


class GradeRecordViewSet(AuditableModelViewSet):
    """CRUD de GradeRecord."""

    queryset = GradeRecord.objects.all()
    serializer_class = GradeRecordSerializer
    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.ACADEMIC_VIEW)]
    search_fields = ["evaluation"]
    ordering_fields = ["created_at"]
    filterset_fields = ["status"]
