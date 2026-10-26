"""Administración Django del módulo Mantenimiento."""

from django.contrib import admin

from apps.maintenance.models import Asset, WorkOrder


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    """Administración de Asset."""

    list_display = tuple(
        f.name
        for f in Asset._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in Asset._meta.fields if f.name in ("code", "name", "title", "label")
    )


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    """Administración de WorkOrder."""

    list_display = tuple(
        f.name
        for f in WorkOrder._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in WorkOrder._meta.fields if f.name in ("code", "name", "title", "label")
    )
