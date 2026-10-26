"""Vistas del módulo (CRUD con RBAC y auditoría automática)."""

from rest_framework import permissions

from apps.usuarios.constants import Permission
from apps.usuarios.rbac import HasPerm, HasPermForWrite
from apps.core.mixins import AuditableModelViewSet  # noqa: F401 (documentación)
from apps.research.models import ProjectMilestone, ResearchProject
from apps.research.serializers import ProjectMilestoneSerializer, ResearchProjectSerializer


class ResearchProjectViewSet(AuditableModelViewSet):
    """CRUD de ResearchProject."""

    queryset = ResearchProject.objects.all()
    serializer_class = ResearchProjectSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        HasPermForWrite(Permission.RESEARCH_MANAGE, Permission.RESEARCH_VIEW),
    ]
    search_fields = ["code", "title", "leader"]
    ordering_fields = ["created_at"]
    filterset_fields = ["status"]


class ProjectMilestoneViewSet(AuditableModelViewSet):
    """CRUD de ProjectMilestone."""

    queryset = ProjectMilestone.objects.all()
    serializer_class = ProjectMilestoneSerializer
    permission_classes = [permissions.IsAuthenticated, HasPerm(Permission.RESEARCH_VIEW)]
    search_fields = ["title"]
    ordering_fields = ["created_at"]
    filterset_fields = ["status"]
