"""Rutas de los nomencladores (sedes, áreas, puntos de control, catálogos)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.catalogs_views import (
    AccessPointViewSet,
    CampusSiteViewSet,
    CatalogEntryViewSet,
    NivelAccesoViewSet,
    OrganizationalUnitViewSet,
)

app_name = "catalogs"

router = DefaultRouter()
router.register("campuses", CampusSiteViewSet, basename="campus")
router.register("units", OrganizationalUnitViewSet, basename="unit")
router.register("access-points", AccessPointViewSet, basename="access-point")
router.register("entries", CatalogEntryViewSet, basename="catalog-entry")
router.register("access-levels", NivelAccesoViewSet, basename="access-level")

urlpatterns = [path("", include(router.urls))]
