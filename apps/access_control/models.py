"""Registros de acceso (bitácora) y validaciones asociadas."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.constants import MovementType
from apps.core.models import BaseModel


class AccessLog(BaseModel):
    """Movimiento registrado en un punto de control (RF-04.5 / RF-08.1).

    Los registros son inmutables por diseño: cualquier corrección debe
    realizarse con un nuevo movimiento, preservando la trazabilidad.
    """

    class Result(models.TextChoices):
        GRANTED = "PERMITIDO", "Permitido"
        DENIED = "DENEGADO", "Denegado"

    class Channel(models.TextChoices):
        WEB = "WEB", "Web"
        PWA = "PWA", "App / PWA"
        MANUAL = "MANUAL", "Manual"

    class Meta:
        verbose_name = "registro de acceso"
        verbose_name_plural = "bitácora de accesos"
        ordering = ("-occurred_at",)
        indexes = [
            models.Index(fields=["-occurred_at"], name="idx_accesslog_occurred"),
            models.Index(fields=["campus", "-occurred_at"], name="idx_accesslog_campus_time"),
            models.Index(fields=["result"], name="idx_accesslog_result"),
            models.Index(fields=["identity_card"], name="idx_accesslog_ci"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["client_uuid"],
                condition=models.Q(client_uuid__isnull=False),
                name="uniq_accesslog_client_uuid",
            )
        ]

    # --- Persona -----------------------------------------------------------
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_logs",
    )
    badge = models.ForeignKey(
        "solapines.Badge",
        verbose_name="solapín",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_logs",
    )
    full_name = models.CharField("nombre completo", max_length=200, blank=True)
    identity_card = models.CharField("CI / pasaporte", max_length=20, blank=True)
    user_type = models.CharField("tipo de usuario", max_length=30, blank=True)
    access_level = models.CharField("nivel de acceso", max_length=20, blank=True)

    # --- Ubicación / operación --------------------------------------------
    campus = models.CharField("sede", max_length=20, blank=True)
    sede = models.ForeignKey(
        "core.CampusSite",
        verbose_name="sede (nomenclador)",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="access_logs",
    )
    access_point = models.ForeignKey(
        "core.AccessPoint",
        verbose_name="punto de control",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_logs",
    )
    movement = models.CharField(
        "movimiento", max_length=10, choices=MovementType.choices, default=MovementType.ENTRY
    )
    result = models.CharField("resultado", max_length=20, choices=Result.choices)
    denial_reason = models.CharField("motivo de denegación", max_length=120, blank=True)
    channel = models.CharField("canal", max_length=10, choices=Channel.choices, default=Channel.WEB)
    observed = models.CharField("observaciones", max_length=255, blank=True)

    # --- Trazabilidad ------------------------------------------------------
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    occurred_at = models.DateTimeField("ocurrido el", default=timezone.now, db_index=True)
    synced_at = models.DateTimeField("sincronizado el", null=True, blank=True)
    client_uuid = models.UUIDField(
        "UUID del cliente", null=True, blank=True, help_text="Idempotencia para registros offline."
    )
    source_ip = models.GenericIPAddressField("IP de origen", null=True, blank=True)
    device_info = models.CharField("dispositivo", max_length=200, blank=True)

    @property
    def fecha_hora(self):
        """Alias de dominio del momento del registro (RF-04.5)."""
        return self.occurred_at

    def __str__(self) -> str:
        return f"{self.occurred_at:%Y-%m-%d %H:%M} · {self.full_name or self.identity_card} · {self.result}"
