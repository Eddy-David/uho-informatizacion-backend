"""Administración Django del módulo Analítica institucional."""

from django.contrib import admin

from apps.analytics.models import DashboardDefinition, KpiDefinition


@admin.register(DashboardDefinition)
class DashboardDefinitionAdmin(admin.ModelAdmin):
    """Administración de DashboardDefinition."""

    list_display = tuple(
        f.name
        for f in DashboardDefinition._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name
        for f in DashboardDefinition._meta.fields
        if f.name in ("code", "name", "title", "label")
    )


@admin.register(KpiDefinition)
class KpiDefinitionAdmin(admin.ModelAdmin):
    """Administración de KpiDefinition."""

    list_display = tuple(
        f.name
        for f in KpiDefinition._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in KpiDefinition._meta.fields if f.name in ("code", "name", "title", "label")
    )
