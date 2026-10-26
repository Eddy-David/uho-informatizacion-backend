"""Administración de la bitácora de accesos (solo consulta)."""

from django.contrib import admin

from apps.access_control.models import AccessLog


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "full_name", "identity_card", "campus", "movement", "result")
    list_filter = ("result", "movement", "campus", "channel")
    search_fields = ("full_name", "identity_card")
    date_hierarchy = "occurred_at"
    ordering = ("-occurred_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
