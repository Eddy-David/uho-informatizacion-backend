"""Serializers del módulo."""

from rest_framework import serializers

from apps.research.models import ProjectMilestone, ResearchProject


class ResearchProjectSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = ResearchProject
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ProjectMilestoneSerializer(serializers.ModelSerializer):
    """Serialización completa con campos de auditoría en solo lectura."""

    class Meta:
        model = ProjectMilestone
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
