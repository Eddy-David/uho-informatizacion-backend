"""Modelos del módulo. Amplíe los campos según los requerimientos."""

from __future__ import annotations

from django.db import models

from apps.core.audit import AuditedModel
from apps.core.models import TimeStampedModel


class Asset(TimeStampedModel, AuditedModel):
    """Activo inventariable."""

    class Meta:
        verbose_name = "activo inventariable"
        verbose_name_plural = "activo inventariables"
        ordering = ("-created_at",)

    code = models.CharField("inventario", max_length=30, unique=True)
    name = models.CharField("nombre", max_length=200)
    kind = models.CharField("tipo", max_length=50, blank=True)
    location = models.CharField("ubicación", max_length=150, blank=True)
    purchased_at = models.DateField("adquirido el", null=True, blank=True)
    status = models.CharField("estado", max_length=20, default="OPERATIVO")

    def __str__(self) -> str:
        return str(getattr(self, "nombre", None) or self.pk)


class WorkOrder(TimeStampedModel, AuditedModel):
    """Orden de mantenimiento."""

    class Meta:
        verbose_name = "orden de mantenimiento"
        verbose_name_plural = "orden de mantenimientos"
        ordering = ("-created_at",)

    asset = models.ForeignKey(
        "maintenance.Asset",
        verbose_name="activo",
        on_delete=models.CASCADE,
        related_name="work_orders",
    )
    title = models.CharField("título", max_length=200)
    priority = models.CharField("prioridad", max_length=10, default="MEDIA")
    scheduled_for = models.DateField("programada para", null=True, blank=True)
    status = models.CharField("estado", max_length=20, default="ABIERTA")
    notes = models.TextField("notas", blank=True)

    def __str__(self) -> str:
        return str(getattr(self, "título", None) or self.pk)
