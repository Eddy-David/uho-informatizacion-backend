"""Rutas de la aplicación core (salud y metadatos)."""

from django.urls import path

from apps.core.views import AboutView, HealthCheckView

app_name = "core"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("about/", AboutView.as_view(), name="about"),
]
