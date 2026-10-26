"""Configuración de la aplicación solapines."""

from django.apps import AppConfig


class SolapinesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.solapines"
    label = "solapines"
    verbose_name = "Solapín digital"
