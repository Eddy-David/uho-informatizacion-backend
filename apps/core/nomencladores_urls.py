"""Rutas de los nomencladores básicos de RF-09.3.

Expone en español las mismas vistas que ``catalog_urls`` (permisos ya definidos
en ``apps/core/permissions.py``: lectura autenticada, escritura de administradores)::

    /api/v1/nomencladores/sedes/
    /api/v1/nomencladores/areas/
    /api/v1/nomencladores/niveles-acceso/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.catalogs_views import (
    CampusSiteViewSet,
    NivelAccesoViewSet,
    OrganizationalUnitViewSet,
)

app_name = "nomencladores"

router = DefaultRouter()
router.register("sedes", CampusSiteViewSet, basename="sede")
router.register("areas", OrganizationalUnitViewSet, basename="area")
router.register("niveles-acceso", NivelAccesoViewSet, basename="nivel-acceso")

urlpatterns = [path("", include(router.urls))]
