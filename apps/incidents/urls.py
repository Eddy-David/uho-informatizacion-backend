"""Rutas del módulo de incidencias."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.incidents.views import IncidentFollowUpViewSet, IncidentViewSet

app_name = "incidents"

router = DefaultRouter()
router.register("", IncidentViewSet, basename="incident")
router.register("follow-ups", IncidentFollowUpViewSet, basename="incident-follow-up")

urlpatterns = [path("", include(router.urls))]
