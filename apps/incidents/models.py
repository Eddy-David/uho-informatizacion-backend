"""Modelo de incidencias."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.constants import Campus
from apps.core.models import AuditModel, BaseModel


class Incident(BaseModel, AuditModel):
    """Incidencia registrada en un punto de acceso (RF-07)."""

    class Severity(models.TextChoices):
        LOW = "BAJA", "Baja"
        MEDIUM = "MEDIA", "Media"
        HIGH = "ALTA", "Alta"
        CRITICAL = "CRITICA", "Crítica"

    class Status(models.TextChoices):
        OPEN = "ABIERTA", "Abierta"
        FOLLOW_UP = "SEGUIMIENTO", "En seguimiento"
        CLOSED = "CERRADA", "Cerrada"
        DISMISSED = "DESESTIMADA", "Desestimada"

    class Meta:
        verbose_name = "incidencia"
        verbose_name_plural = "incidencias"
        ordering = ("-occurred_at",)
        indexes = [
            models.Index(fields=["status"], name="idx_incident_status"),
            models.Index(fields=["-occurred_at"], name="idx_incident_occurred"),
        ]

    code = models.CharField("código", max_length=20, unique=True, blank=True)
    title = models.CharField("título", max_length=200)
    description = models.TextField("descripción")
    incident_type = models.CharField("tipo", max_length=50)
    severity = models.CharField(
        "gravedad", max_length=10, choices=Severity.choices, default=Severity.MEDIUM
    )
    status = models.CharField("estado", max_length=15, choices=Status.choices, default=Status.OPEN)

    campus = models.CharField("sede", max_length=20, choices=Campus.choices)
    access_point = models.ForeignKey(
        "core.AccessPoint",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incidents",
    )

    # --- Relaciones con otros eventos -------------------------------------
    access_log = models.ForeignKey(
        "access_control.AccessLog",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incidents",
    )
    visit_request = models.ForeignKey(
        "visitors.VisitRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incidents",
    )
    vehicle_movement = models.ForeignKey(
        "vehicles.VehicleMovement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incidents",
    )

    person_name = models.CharField("persona involucrada", max_length=200, blank=True)
    person_identity_card = models.CharField("CI de la persona", max_length=11, blank=True)
    photo = models.ImageField(
        "evidencia fotográfica", upload_to="incidents/", null=True, blank=True
    )

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="reportada por",
        on_delete=models.PROTECT,
        related_name="reported_incidents",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="asignada a",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_incidents",
    )
    occurred_at = models.DateTimeField("ocurrida el", default=timezone.now)
    closed_at = models.DateTimeField("cerrada el", null=True, blank=True)
    resolution = models.TextField("resolución / acciones", blank=True)

    def __str__(self) -> str:
        return f"{self.code} · {self.title}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"INC-{timezone.now():%Y%m%d}-{self.uuid.hex[:4].upper()}"
        if self.status == self.Status.CLOSED and self.closed_at is None:
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)


class IncidentFollowUp(BaseModel):
    """Seguimiento cronológico de una incidencia."""

    class Meta:
        verbose_name = "seguimiento de incidencia"
        verbose_name_plural = "seguimientos de incidencias"
        ordering = ("-created_at",)

    incident = models.ForeignKey(
        Incident, verbose_name="incidencia", on_delete=models.CASCADE, related_name="follow_ups"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    comment = models.TextField("comentario")
    new_status = models.CharField(
        "nuevo estado", max_length=15, choices=Incident.Status.choices, blank=True
    )

    def __str__(self) -> str:
        return f"{self.incident.code} · {self.created_at:%Y-%m-%d %H:%M}"
