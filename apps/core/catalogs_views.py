"""Vistas de nomencladores (CRUD para administradores, lectura autenticada)."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions

from apps.core.catalogs import (
    AccessPoint,
    CampusSite,
    CatalogEntry,
    NivelAcceso,
    OrganizationalUnit,
)
from apps.core.catalogs_serializers import (
    AccessPointSerializer,
    CampusSiteSerializer,
    CatalogEntrySerializer,
    NivelAccesoSerializer,
    OrganizationalUnitSerializer,
)
from apps.core.mixins import AuditableModelViewSet
from apps.core.permissions import ReadOnlyOrAdmin


class CampusSiteViewSet(AuditableModelViewSet):
    """Sedes de la Universidad de Holguín."""

    queryset = CampusSite.objects.all()
    serializer_class = CampusSiteSerializer
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "code"]
    lookup_field = "uuid"


class OrganizationalUnitViewSet(AuditableModelViewSet):
    """Áreas organizativas (facultades y dependencias)."""

    queryset = OrganizationalUnit.objects.select_related("campus")
    serializer_class = OrganizationalUnitSerializer
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["campus", "status"]
    search_fields = ["name", "acronym"]
    ordering_fields = ["name"]
    lookup_field = "uuid"


class AccessPointViewSet(AuditableModelViewSet):
    """Puntos de control (peatonales y vehiculares)."""

    queryset = AccessPoint.objects.select_related("campus")
    serializer_class = AccessPointSerializer
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["campus", "is_vehicle_access", "status"]
    search_fields = ["name", "code"]
    ordering_fields = ["name"]
    lookup_field = "uuid"


class CatalogEntryViewSet(AuditableModelViewSet):
    """Nomencladores administrables (tipos de vehículo, incidencias, etc.)."""

    queryset = CatalogEntry.objects.all()
    serializer_class = CatalogEntrySerializer
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["kind", "is_active"]
    search_fields = ["code", "name"]
    ordering_fields = ["kind", "sort_order", "name"]
    lookup_field = "uuid"


class NivelAccesoViewSet(AuditableModelViewSet):
    """Niveles de acceso oficiales del solapín (RF-09.3)."""

    queryset = NivelAcceso.objects.all()
    serializer_class = NivelAccesoSerializer
    permission_classes = [permissions.IsAuthenticated, ReadOnlyOrAdmin]
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["nombre", "sort_order"]
    lookup_field = "uuid"
