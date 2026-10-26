"""Administración Django de la auditoría (solo consulta)."""

from django.contrib import admin

from apps.core.audit import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "module",
        "actor_username",
        "target_repr",
        "severity",
        "ip_address",
    )
    list_filter = ("action", "severity", "module")
    search_fields = ("actor_username", "description", "target_repr", "target_id", "ip_address")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = [field.name for field in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
