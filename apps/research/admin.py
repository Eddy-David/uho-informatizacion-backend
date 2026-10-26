"""Administración Django del módulo Proyectos de investigación."""

from django.contrib import admin

from apps.research.models import ProjectMilestone, ResearchProject


@admin.register(ResearchProject)
class ResearchProjectAdmin(admin.ModelAdmin):
    """Administración de ResearchProject."""

    list_display = tuple(
        f.name
        for f in ResearchProject._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in ResearchProject._meta.fields if f.name in ("code", "name", "title", "label")
    )


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    """Administración de ProjectMilestone."""

    list_display = tuple(
        f.name
        for f in ProjectMilestone._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name
        for f in ProjectMilestone._meta.fields
        if f.name in ("code", "name", "title", "label")
    )
