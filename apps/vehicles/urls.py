"""Rutas del módulo de vehículos."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.vehicles.views import (
    AuthorizedVehicleViewSet,
    RegisterVehicleMovementView,
    VehicleCheckView,
    VehicleMovementViewSet,
    VehicleTypesView,
)

app_name = "vehicles"

router = DefaultRouter()
router.register("authorized", AuthorizedVehicleViewSet, basename="authorized-vehicle")
router.register("movements", VehicleMovementViewSet, basename="vehicle-movement")

urlpatterns = [
    path("check/", VehicleCheckView.as_view(), name="check"),
    path("register/", RegisterVehicleMovementView.as_view(), name="register"),
    path("types/", VehicleTypesView.as_view(), name="types"),
    path("", include(router.urls)),
]
