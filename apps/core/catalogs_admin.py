"""Administración Django de los nomencladores compartidos."""

from django.contrib import admin

from apps.core.catalogs import (
    AccessPoint,
    CampusSite,
    CatalogEntry,
    NivelAcceso,
    OrganizationalUnit,
)


@admin.register(CampusSite)
class CampusSiteAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "municipality", "status")
    search_fields = ("name", "code")
    list_filter = ("status",)


@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "acronym", "campus", "status")
    search_fields = ("name", "acronym")
    list_filter = ("campus", "status")


@admin.register(AccessPoint)
class AccessPointAdmin(admin.ModelAdmin):
    list_display = ("name", "campus", "code", "is_vehicle_access", "status")
    list_filter = ("campus", "is_vehicle_access", "status")
    search_fields = ("name", "code")


@admin.register(CatalogEntry)
class CatalogEntryAdmin(admin.ModelAdmin):
    list_display = ("kind", "code", "name", "is_active", "sort_order")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name")


@admin.register(NivelAcceso)
class NivelAccesoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "sort_order", "descripcion")
    search_fields = ("nombre", "descripcion")
    ordering = ("sort_order",)
