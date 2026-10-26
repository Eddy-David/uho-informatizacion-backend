"""Administración Django del Solapín Digital."""

from django.contrib import admin

from apps.solapines.models import Badge, BadgePrintJob, BadgeTemplate


@admin.register(BadgeTemplate)
class BadgeTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "user_type", "campus", "is_default", "status")
    list_filter = ("user_type", "campus", "is_default", "status")
    search_fields = ("name",)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("badge_number", "user", "access_level", "status", "issued_at", "expires_at")
    list_filter = ("status", "access_level")
    search_fields = ("badge_number", "user__ci", "user__nombres", "user__apellidos")
    readonly_fields = ("qr_token", "issued_at")


@admin.register(BadgePrintJob)
class BadgePrintJobAdmin(admin.ModelAdmin):
    list_display = ("uuid", "campus", "user_type", "total", "processed", "status", "created_at")
    list_filter = ("status", "campus", "user_type")
