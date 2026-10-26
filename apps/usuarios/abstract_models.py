"""Usuario institucional según el modelo conceptual de datos (requisitos.md, §5).

Al igual que en las versiones anteriores del proyecto, el perfil se implementa
con un ``abstract`` model para poder importarlo desde las migraciones
históricas (``UserManager`` se serializa con ``use_in_migrations``).
No define ``Meta.app_label`` ni ``db_table``: la tabla física es
``usuarios_usuario`` y la genera la migración de la app ``usuarios``.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.constants import AccessLevel, Campus, Role, UserType


class UserManager(BaseUserManager):
    """Gestor del usuario institucional (identificado por su usuario de red)."""

    use_in_migrations = True

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError("El nombre de usuario es obligatorio.")
        username = username.strip().lower()
        email = (extra_fields.get("email") or "").strip().lower()
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.SUPERADMIN)
        extra_fields.setdefault("tipo_usuario", UserType.WORKER)
        extra_fields.setdefault("nivel_acceso", AccessLevel.FREE)
        extra_fields.setdefault("estado", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_superuser=True.")
        return self._create_user(username, password, **extra_fields)


class UserAbstract(AbstractBaseUser, PermissionsMixin):
    """Datos personales, académicos y de acceso de la persona (requisitos §5).

    Los campos oficiales (nombre, apellidos, CI y tipo de usuario) provienen de
    AGA_AUTH/SIGENU/ASSET y no se editan manualmente (regla de negocio 4).
    """

    class Meta:
        abstract = True
        ordering = ("apellidos", "nombres")

    # --- Identificación -----------------------------------------------------
    ci = models.CharField(
        "carnet de identidad",
        max_length=11,
        blank=True,
        db_index=True,
        help_text="Documento de identidad emitido por SIGENU/ASSET; no editable.",
    )
    nombres = models.CharField("nombres", max_length=80)
    apellidos = models.CharField("apellidos", max_length=120)
    foto = models.ImageField("foto", upload_to="users/photos/", null=True, blank=True)
    tipo_usuario = models.CharField(
        "tipo de usuario", max_length=20, choices=UserType.choices, default=UserType.WORKER
    )

    # --- Datos laborales (trabajadores y cuadros) ---------------------------
    area = models.CharField("área", max_length=150, blank=True)
    cargo = models.CharField("cargo", max_length=120, blank=True)

    # --- Datos académicos (estudiantes) -------------------------------------
    facultad = models.CharField("facultad", max_length=150, blank=True)
    carrera = models.CharField("carrera", max_length=150, blank=True)
    ano = models.PositiveSmallIntegerField("año", null=True, blank=True)

    # --- Estado y acceso ----------------------------------------------------
    estado = models.BooleanField("persona activa", default=True, db_index=True)
    campus_sede = models.CharField("sede", max_length=20, choices=Campus.choices, blank=True)
    nivel_acceso = models.CharField(
        "nivel de acceso",
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.LIMITED,
    )
    fecha_alta = models.DateTimeField("fecha de alta", default=timezone.now)
    fecha_baja = models.DateTimeField("fecha de baja", null=True, blank=True)

    # --- Acceso al sistema --------------------------------------------------
    role = models.CharField(
        "rol", max_length=10, choices=Role.choices, default=Role.USER, db_index=True
    )
    is_staff = models.BooleanField("acceso al admin", default=False)
