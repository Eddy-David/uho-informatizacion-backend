"""Catálogo de vehículos autorizados y sus movimientos."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.constants import Campus, MovementType
from apps.core.models import AuditModel, BaseModel


class AuthorizedVehicle(BaseModel, AuditModel):
    """Vehículo con autorización permanente (RF-06.2 / RF-06.3)."""

    class Meta:
        verbose_name = "vehículo autorizado"
        verbose_name_plural = "vehículos autorizados"
        ordering = ("plate",)
        constraints = [models.UniqueConstraint(fields=["plate"], name="uniq_vehicle_plate")]
        indexes = [models.Index(fields=["plate"], name="idx_vehicle_plate")]

    plate = models.CharField("placa", max_length=20, unique=True)
    vehicle_type = models.CharField("tipo de vehículo", max_length=50, default="Automóvil")
    brand = models.CharField("marca", max_length=80, blank=True)
    model = models.CharField("modelo", max_length=80, blank=True)
    color = models.CharField("color", max_length=40, blank=True)
    owner_name = models.CharField("propietario / área", max_length=150)
    owner_identity_card = models.CharField("CI del propietario", max_length=11, blank=True)
    campus = models.CharField("sede", max_length=20, choices=Campus.choices, blank=True)
    authorization_reason = models.CharField("motivo de autorización", max_length=200)
    valid_from = models.DateField("válido desde", default=timezone.localdate)
    valid_until = models.DateField(
        "válido hasta", null=True, blank=True, help_text="Vacío = indefinida"
    )
    is_active = models.BooleanField("activo", default=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="aprobado por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    def __str__(self) -> str:
        return f"{self.plate} · {self.owner_name}"

    @property
    def is_valid(self) -> bool:
        today = timezone.localdate()
        if not self.is_active:
            return False
        if self.valid_from and self.valid_from > today:
            return False
        if self.valid_until and self.valid_until < today:
            return False
        return True

    def save(self, *args, **kwargs):
        self.plate = self.plate.strip().upper()
        super().save(*args, **kwargs)


class VehicleMovement(BaseModel):
    """Registro de entrada/salida de un vehículo (RF-06.1 / RF-06.4)."""

    class Status(models.TextChoices):
        INSIDE = "DENTRO", "Dentro"
        OUTSIDE = "FUERA", "Fuera"

    class Meta:
        verbose_name = "movimiento de vehículo"
        verbose_name_plural = "movimientos de vehículos"
        ordering = ("-occurred_at",)
        indexes = [
            models.Index(fields=["plate", "-occurred_at"], name="idx_vehicle_move_plate"),
            models.Index(fields=["campus", "-occurred_at"], name="idx_vehicle_move_campus"),
        ]

    vehicle = models.ForeignKey(
        AuthorizedVehicle,
        verbose_name="vehículo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movements",
    )
    plate = models.CharField("placa", max_length=20)
    vehicle_type = models.CharField("tipo de vehículo", max_length=50, blank=True)
    driver_name = models.CharField("conductor", max_length=150, blank=True)
    driver_identity_card = models.CharField("CI del conductor", max_length=11, blank=True)
    campus = models.CharField("sede", max_length=20, choices=Campus.choices, blank=True)
    access_point = models.ForeignKey(
        "core.AccessPoint", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    movement = models.CharField("movimiento", max_length=10, choices=MovementType.choices)
    authorized = models.BooleanField("autorizado", default=False)
    is_exception = models.BooleanField("entrada por excepción", default=False)
    reason = models.CharField("motivo / observaciones", max_length=255, blank=True)
    status_after = models.CharField("estado", max_length=10, choices=Status.choices)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    occurred_at = models.DateTimeField("ocurrido el", default=timezone.now)

    def __str__(self) -> str:
        return f"{self.plate} · {self.movement} · {self.occurred_at:%Y-%m-%d %H:%M}"
