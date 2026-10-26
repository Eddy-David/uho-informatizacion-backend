"""Rutas del módulo ``analytics``."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.analytics.views import DashboardDefinitionViewSet, KpiDefinitionViewSet

app_name = "analytics"

router = DefaultRouter()
router.register(
    "dashboard_definitions", DashboardDefinitionViewSet, basename="dashboard_definition"
)
router.register("kpi_definitions", KpiDefinitionViewSet, basename="kpi_definition")

urlpatterns = [path("", include(router.urls))]
