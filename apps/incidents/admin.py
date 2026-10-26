"""Administración Django del módulo de incidencias."""

from django.contrib import admin

from apps.incidents.models import Incident, IncidentFollowUp


class FollowUpInline(admin.TabularInline):
    model = IncidentFollowUp
    extra = 0
    readonly_fields = ("author", "created_at")


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "incident_type", "severity", "status", "campus", "occurred_at")
    list_filter = ("status", "severity", "campus", "incident_type")
    search_fields = ("code", "title", "person_name", "person_identity_card")
    date_hierarchy = "occurred_at"
    inlines = [FollowUpInline]


@admin.register(IncidentFollowUp)
class IncidentFollowUpAdmin(admin.ModelAdmin):
    list_display = ("incident", "author", "new_status", "created_at")
