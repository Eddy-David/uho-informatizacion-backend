"""Administración Django del modelo de usuario."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.usuarios.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("apellidos", "nombres")
    list_display = (
        "username",
        "nombre_completo",
        "ci",
        "role",
        "tipo_usuario",
        "campus_sede",
        "estado",
        "last_login",
    )
    list_filter = ("role", "tipo_usuario", "campus_sede", "estado", "is_staff", "is_superuser")
    search_fields = ("username", "nombres", "apellidos", "ci", "email")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Datos personales"),
            {
                "fields": (
                    "nombres",
                    "apellidos",
                    "ci",
                    "foto",
                    "birth_date",
                    "sex",
                    "email",
                    "phone",
                )
            },
        ),
        (
            _("Datos laborales y académicos"),
            {
                "fields": (
                    "tipo_usuario",
                    "area",
                    "cargo",
                    "facultad",
                    "carrera",
                    "ano",
                )
            },
        ),
        (
            _("Datos institucionales"),
            {
                "fields": (
                    "role",
                    "campus_sede",
                    "nivel_acceso",
                    "external_id",
                    "sync_source",
                    "last_sync_at",
                )
            },
        ),
        (
            _("Permisos"),
            {
                "fields": (
                    "estado",
                    "is_staff",
                    "is_superuser",
                    "must_change_password",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Auditoría"), {"fields": ("last_login", "last_login_ip", "fecha_alta")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "nombres",
                    "apellidos",
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "tipo_usuario",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "last_login_ip", "fecha_alta")
