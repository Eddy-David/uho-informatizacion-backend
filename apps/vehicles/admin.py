"""Administración Django del módulo de vehículos."""

from django.contrib import admin

from apps.vehicles.models import AuthorizedVehicle, VehicleMovement


@admin.register(AuthorizedVehicle)
class AuthorizedVehicleAdmin(admin.ModelAdmin):
    list_display = ("plate", "vehicle_type", "owner_name", "campus", "valid_until", "is_active")
    list_filter = ("campus", "vehicle_type", "is_active")
    search_fields = ("plate", "owner_name")


@admin.register(VehicleMovement)
class VehicleMovementAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "plate", "movement", "campus", "authorized", "status_after")
    list_filter = ("campus", "movement", "authorized", "is_exception")
    search_fields = ("plate", "driver_name")
    date_hierarchy = "occurred_at"

    def has_add_permission(self, request):
        return False
