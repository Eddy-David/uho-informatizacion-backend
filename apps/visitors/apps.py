"""Configuración de la aplicación visitors."""

from django.apps import AppConfig


class VisitorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.visitors"
    label = "visitors"
    verbose_name = "Visitantes"
