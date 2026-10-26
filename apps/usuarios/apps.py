"""Configuración de la aplicación usuarios."""

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.usuarios"
    label = "usuarios"
    verbose_name = "Usuarios y roles"

    def ready(self):
        """Registra las señales de ciclo de vida del usuario."""
        from . import signals  # noqa: F401  (registro de señales)
