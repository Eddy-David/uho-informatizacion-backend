"""Configuración de la aplicación core."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "Núcleo del sistema"

    def ready(self):
        """Registra la auditoría automática de los modelos auditados."""
        from apps.core.audit import register_audit_signals

        register_audit_signals()
