"""Administración Django del módulo Procesos académicos."""

from django.contrib import admin

from apps.academic.models import AcademicPeriod, Course, GradeRecord


@admin.register(AcademicPeriod)
class AcademicPeriodAdmin(admin.ModelAdmin):
    """Administración de AcademicPeriod."""

    list_display = tuple(
        f.name
        for f in AcademicPeriod._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in AcademicPeriod._meta.fields if f.name in ("code", "name", "title", "label")
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Administración de Course."""

    list_display = tuple(
        f.name
        for f in Course._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in Course._meta.fields if f.name in ("code", "name", "title", "label")
    )


@admin.register(GradeRecord)
class GradeRecordAdmin(admin.ModelAdmin):
    """Administración de GradeRecord."""

    list_display = tuple(
        f.name
        for f in GradeRecord._meta.fields
        if f.name in ("id", "code", "name", "title", "label", "status")
    )
    search_fields = tuple(
        f.name for f in GradeRecord._meta.fields if f.name in ("code", "name", "title", "label")
    )
