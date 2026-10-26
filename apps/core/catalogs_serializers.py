"""Serializers de nomencladores."""

from rest_framework import serializers

from apps.core.catalogs import (
    AccessPoint,
    CampusSite,
    CatalogEntry,
    NivelAcceso,
    OrganizationalUnit,
)
from apps.core.constants import RecordStatus


class CampusSiteSerializer(serializers.ModelSerializer):
    # ``activo`` es la vista pública de ``status``: se puede leer y escribir.
    activo = serializers.BooleanField(required=False)

    class Meta:
        model = CampusSite
        fields = (
            "id",
            "uuid",
            "code",
            "name",
            "address",
            "municipality",
            "province",
            "phone",
            "status",
            "activo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")

    def validate(self, attrs):
        if "activo" in self.initial_data:
            attrs["status"] = RecordStatus.ACTIVE if attrs.pop("activo") else RecordStatus.INACTIVE
        return attrs


class OrganizationalUnitSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)
    activo = serializers.BooleanField(required=False)

    class Meta:
        model = OrganizationalUnit
        fields = (
            "id",
            "uuid",
            "campus",
            "campus_name",
            "name",
            "acronym",
            "status",
            "activo",
        )
        read_only_fields = ("id", "uuid")

    def validate(self, attrs):
        if "activo" in self.initial_data:
            attrs["status"] = RecordStatus.ACTIVE if attrs.pop("activo") else RecordStatus.INACTIVE
        return attrs


class AccessPointSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)

    class Meta:
        model = AccessPoint
        fields = (
            "id",
            "uuid",
            "code",
            "name",
            "campus",
            "campus_name",
            "is_vehicle_access",
            "status",
        )
        read_only_fields = ("id", "uuid")


class CatalogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogEntry
        fields = (
            "id",
            "uuid",
            "kind",
            "code",
            "name",
            "description",
            "sort_order",
            "is_active",
        )
        read_only_fields = ("id", "uuid")


class NivelAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NivelAcceso
        fields = (
            "id",
            "uuid",
            "nombre",
            "descripcion",
            "sort_order",
            "codigo_acceso",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "uuid", "codigo_acceso", "created_at", "updated_at")
