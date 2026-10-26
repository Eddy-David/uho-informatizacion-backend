"""Modelo de notificaciones."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Notification(BaseModel):
    """Notificación dirigida a un usuario."""

    class Category(models.TextChoices):
        SYSTEM = "SISTEMA", "Sistema"
        ACCESS = "ACCESO", "Control de acceso"
        CREDENTIAL = "SOLAPIN", "Solapín digital"
        VISIT = "VISITA", "Visitantes"
        VEHICLE = "VEHICULO", "Vehículos"
        INCIDENT = "INCIDENCIA", "Incidencia"
        SECURITY = "SEGURIDAD", "Alerta de seguridad"

    class Priority(models.TextChoices):
        LOW = "BAJA", "Baja"
        NORMAL = "NORMAL", "Normal"
        HIGH = "ALTA", "Alta"

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "is_read"], name="idx_notification_user_read"),
            models.Index(fields=["-created_at"], name="idx_notification_created"),
        ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="destinatario",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField("título", max_length=200)
    message = models.TextField("mensaje")
    category = models.CharField(
        "categoría", max_length=15, choices=Category.choices, default=Category.SYSTEM
    )
    priority = models.CharField(
        "prioridad", max_length=10, choices=Priority.choices, default=Priority.NORMAL
    )
    link = models.CharField("enlace", max_length=300, blank=True)
    payload = models.JSONField("datos adicionales", default=dict, blank=True)
    is_read = models.BooleanField("leída", default=False, db_index=True)
    read_at = models.DateTimeField("leída el", null=True, blank=True)
    email_sent = models.BooleanField("enviada por correo", default=False)

    def __str__(self) -> str:
        return f"{self.user.username} · {self.title}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])
