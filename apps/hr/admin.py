"""Administración Django del módulo Recursos humanos."""

from django.contrib import admin

from apps.hr.models import EmployeeRecord, LeaveRequest, Position


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    """Administración de Position."""

    list_display = tuple(
        f.name
        for f in Position._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in Position._meta.fields if f.name in ("code", "name", "title", "label")
    )


@admin.register(EmployeeRecord)
class EmployeeRecordAdmin(admin.ModelAdmin):
    """Administración de EmployeeRecord."""

    list_display = tuple(
        f.name
        for f in EmployeeRecord._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in EmployeeRecord._meta.fields if f.name in ("code", "name", "title", "label")
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    """Administración de LeaveRequest."""

    list_display = tuple(
        f.name
        for f in LeaveRequest._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in LeaveRequest._meta.fields if f.name in ("code", "name", "title", "label")
    )
