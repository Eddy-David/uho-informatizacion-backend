# Registro de auditoría (solo lectura desde el admin).
from django.contrib import admin

from apps.auditoria.models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = (
        "fecha_hora",
        "usuario",
        "modulo",
        "accion",
        "ruta",
        "status_code",
        "ip_address",
    )
    list_filter = ("modulo", "accion", "status_code")
    search_fields = ("usuario__username", "modulo", "accion", "ruta", "request_id")
    readonly_fields = (
        "usuario",
        "modulo",
        "accion",
        "detalle",
        "fecha_hora",
        "ip_address",
        "user_agent",
        "request_id",
        "method",
        "ruta",
        "status_code",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
