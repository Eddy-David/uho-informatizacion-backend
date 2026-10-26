"""Administración Django del módulo Gestión estudiantil."""

from django.contrib import admin

from apps.students.models import Enrollment, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Administración de StudentProfile."""

    list_display = tuple(
        f.name
        for f in StudentProfile._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in StudentProfile._meta.fields if f.name in ("code", "name", "title", "label")
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """Administración de Enrollment."""

    list_display = tuple(
        f.name
        for f in Enrollment._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in Enrollment._meta.fields if f.name in ("code", "name", "title", "label")
    )
