"""Administración Django del módulo de visitantes."""

from django.contrib import admin

from apps.visitors.models import Visitor, VisitRequest


@admin.register(VisitRequest)
class VisitRequestAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "visitor_name",
        "requester",
        "area",
        "campus",
        "valid_from",
        "valid_until",
        "status",
    )
    list_filter = ("status", "campus")
    search_fields = ("code", "visitor_name", "visitor_identity_card")
    date_hierarchy = "created_at"


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "identity_card",
        "campus",
        "valid_from",
        "valid_until",
        "checked_in_at",
    )
    list_filter = ("campus",)
    search_fields = ("full_name", "identity_card")
