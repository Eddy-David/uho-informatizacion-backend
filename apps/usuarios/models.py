"""Modelo de usuario personalizado y catálogo de permisos por rol."""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

from apps.usuarios.abstract_models import UserAbstract, UserManager
from apps.usuarios.constants import RoleCode, default_permissions_for
from apps.core.constants import AccessLevel, Role


class User(UserAbstract):
    """Usuario del sistema, alimentado desde AGA_AUTH / SIGENU (requisitos §5).

    Identidad institucional: ``id, ci, nombres, apellidos, tipo_usuario, foto,
    área_cargo (area + cargo), facultad, carrera, año, estado, roles``. Se usa
    ``username`` (usuario de red) como campo de autenticación ante AGA_AUTH.
    """

    class Meta(UserAbstract.Meta):
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        db_table = "usuarios_usuario"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # --- Datos de contacto --------------------------------------------------
    username = models.CharField("usuario de red", max_length=80, unique=True)
    email = models.EmailField("correo electrónico", blank=True, null=True, unique=True)
    birth_date = models.DateField("fecha de nacimiento", null=True, blank=True)
    sex = models.CharField(
        "sexo",
        max_length=1,
        choices=(("F", "Femenino"), ("M", "Masculino")),
        blank=True,
    )
    phone = models.CharField("teléfono", max_length=30, blank=True)

    # --- Integraciones ------------------------------------------------------
    external_id = models.CharField("ID en SIGENU/ASSET", max_length=64, blank=True, db_index=True)
    sync_source = models.CharField(
        "origen de sincronización",
        max_length=20,
        choices=(("LOCAL", "Local"), ("AGA_AUTH", "AGA_AUTH"), ("SIGENU", "SIGENU")),
        default="LOCAL",
    )
    last_sync_at = models.DateTimeField("sincronizado el", null=True, blank=True)
    last_login_ip = models.GenericIPAddressField("última IP", null=True, blank=True)
    must_change_password = models.BooleanField("debe cambiar contraseña", default=False)

    # --- Control de acceso granular ----------------------------------------
    # Los permisos puntuales se suman a los del rol; nunca los restan.
    extra_permissions = models.JSONField(
        "permisos adicionales",
        default=list,
        blank=True,
        help_text="Permisos 'recurso:accion' concedidos a este usuario además de su rol.",
    )
    failed_login_attempts = models.PositiveSmallIntegerField("intentos fallidos", default=0)
    locked_until = models.DateTimeField("bloqueado hasta", null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nombres", "apellidos"]

    class Meta(UserAbstract.Meta):
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        db_table = "usuarios_usuario"

    def __str__(self) -> str:
        return f"{self.nombre_completo} ({self.username})"

    # ------------------------------------------------------------------
    # Alias en inglés: permiten que las piezas genéricas de Django
    # (admin, permisos, sesiones) y los serializers sigan funcionando.
    # ------------------------------------------------------------------
    @property
    def first_name(self) -> str:
        return self.nombres

    @first_name.setter
    def first_name(self, value: str) -> None:
        self.nombres = value

    @property
    def last_name(self) -> str:
        return self.apellidos

    @last_name.setter
    def last_name(self, value: str) -> None:
        self.apellidos = value

    def get_full_name(self) -> str:
        return self.nombre_completo

    def get_short_name(self) -> str:
        return self.nombres

    @property
    def identity_card(self) -> str:
        return self.ci or ""

    @identity_card.setter
    def identity_card(self, value: str) -> None:
        self.ci = value if value is not None else ""

    @property
    def user_type(self) -> str:
        return self.tipo_usuario

    @user_type.setter
    def user_type(self, value: str) -> None:
        self.tipo_usuario = value

    @property
    def position(self) -> str:
        return self.cargo

    @position.setter
    def position(self, value: str) -> None:
        self.cargo = value

    @property
    def campus(self) -> str:
        return self.campus_sede

    @campus.setter
    def campus(self, value: str) -> None:
        self.campus_sede = value

    @property
    def access_level(self) -> str:
        return self.nivel_acceso

    @access_level.setter
    def access_level(self, value: str) -> None:
        self.nivel_acceso = value

    @property
    def is_active(self) -> bool:
        return self.estado

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.estado = value

    @property
    def date_joined(self):
        return self.fecha_alta

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}".strip() or self.username

    @property
    def initials(self) -> str:
        parts = [self.nombres[:1], self.apellidos[:1]]
        return "".join(parts).upper() or self.username[:2].upper()

    @property
    def is_admin_role(self) -> bool:
        return self.is_superuser or self.role in (Role.SUPERADMIN, Role.ADMIN)

    @property
    def is_access_operator(self) -> bool:
        return self.is_superuser or self.role in (
            Role.SUPERADMIN,
            Role.ADMIN,
            Role.SECURITY_DIRECTOR,
            Role.SECURITY_OFFICER,
        )

    def permissions_for_ui(self) -> list[str]:
        """Permisos efectivos (resueltos por rol + concesiones individuales)."""
        from apps.usuarios.rbac import effective_permissions

        return effective_permissions(self)

    def has_perm(self, *permissions: str) -> bool:
        """Comprueba permisos RBAC del SIGACU (distinto de ``has_perm`` de Django)."""
        from apps.usuarios.rbac import user_has

        return user_has(self, *permissions)

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > timezone.now())

    def register_failed_login(self) -> None:
        """Incrementa el contador y bloquea la cuenta al superar el umbral."""
        from apps.usuarios.constants import LOGIN_LOCKOUT_MINUTES, MAX_LOGIN_ATTEMPTS

        self.failed_login_attempts += 1
        if self.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
            self.failed_login_attempts = 0
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def reset_failed_login(self) -> None:
        if self.failed_login_attempts or self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(update_fields=["failed_login_attempts", "locked_until"])

    def save(self, *args, **kwargs):
        # El correo y la CI son únicos y opcionales: se guardan como cadena vacía
        # (nunca NULL) para no chocar con la restricción UNIQUE al dar de alta
        # varias personas sin correo o sin CI registrada.
        if self.email:
            self.email = self.email.strip().lower()
        else:
            self.email = None
        self.ci = (self.ci or "").strip()
        if self.username:
            self.username = self.username.strip().lower()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Rol editable en base de datos
# ---------------------------------------------------------------------------
class RoleDefinition(models.Model):
    """Rol institucional con su conjunto de permisos.

    La matriz por defecto vive en ``apps.usuarios.constants.ROLE_DEFINITIONS`` y se
    sincroniza con ``python manage.py sync_roles``. Un superadministrador puede
    ajustar los permisos desde la API sin modificar el código; los cambios se
    reflejan en la caché de RBAC de inmediato.
    """

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ("sort_order", "label")
        db_table = "usuarios_rol"
        default_permissions = ("add", "change", "delete", "view")

    code = models.CharField("código", max_length=20, unique=True, choices=RoleCode.choices)
    label = models.CharField("nombre", max_length=120)
    description = models.TextField("descripción", blank=True)
    module = models.CharField("módulo funcional", max_length=40, default="core")
    permissions = models.JSONField(
        "permisos",
        default=list,
        blank=True,
        help_text="Lista de permisos 'recurso:accion' o ['*'] para acceso total.",
    )
    is_active = models.BooleanField("activo", default=True)
    is_system = models.BooleanField("rol del sistema", default=False, editable=False)
    sort_order = models.PositiveIntegerField("orden", default=0)
    created_at = models.DateTimeField("creado el", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado el", auto_now=True)

    def __str__(self) -> str:
        return f"{self.label} ({self.code})"

    def clean(self):
        from django.core.exceptions import ValidationError

        from apps.usuarios.constants import ALL_PERMISSIONS

        invalid = [p for p in self.permissions or [] if p != "*" and p not in ALL_PERMISSIONS]
        if invalid:
            raise ValidationError({"permissions": f"Permisos no válidos: {', '.join(invalid)}"})

    def save(self, *args, **kwargs):
        from apps.usuarios.rbac import invalidate_role_cache

        super().save(*args, **kwargs)
        invalidate_role_cache(self.code)

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ValueError("Los roles del sistema no se pueden eliminar; desactívelos.")
        super().delete(*args, **kwargs)


# Compatibilidad con el código que importaba ``ROLE_MODULES`` desde este módulo.
ROLE_MODULES = {code: default_permissions_for(code.value) for code in RoleCode}
