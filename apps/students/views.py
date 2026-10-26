"""Vistas del módulo (CRUD con RBAC y auditoría automática)."""

from rest_framework import permissions

from apps.usuarios.constants import Permission
from apps.usuarios.rbac import HasPerm, HasPermForWrite
from apps.core.mixins import AuditableModelViewSet  # noqa: F401 (documentación)
from apps.students.models import Enrollment, StudentProfile
from apps.students.serializers import EnrollmentSerializer, StudentProfileSerializer


class StudentProfileViewSet(AuditableModelViewSet):
    """CRUD de StudentProfile."""

    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasPermForWrite(Permission.STUDENTS_MANAGE, Permission.STUDENTS_VIEW),
    ]
    search_fields = ["student_number", "career", "group"]
    ordering_fields = ["created_at"]
    filterset_fields = ["status"]


class EnrollmentViewSet(AuditableModelViewSet):
    """CRUD de Enrollment."""

    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.STUDENTS_VIEW)]
    search_fields = ["student__student_number"]
    ordering_fields = ["created_at"]
    filterset_fields = []
