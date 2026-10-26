"""Rutas del módulo ``maintenance``."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.maintenance.views import AssetViewSet, WorkOrderViewSet

app_name = "maintenance"

router = DefaultRouter()
router.register("assets", AssetViewSet, basename="asset")
router.register("work_orders", WorkOrderViewSet, basename="work_order")

urlpatterns = [path("", include(router.urls))]
