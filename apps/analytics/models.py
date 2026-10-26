"""Modelos del módulo. Amplíe los campos según los requerimientos."""

from __future__ import annotations

from django.db import models

from apps.core.audit import AuditedModel
from apps.core.models import TimeStampedModel


class DashboardDefinition(TimeStampedModel, AuditedModel):
    """Tablero analítico."""

    class Meta:
        verbose_name = "tablero analítico"
        verbose_name_plural = "tablero analíticos"
        ordering = ("-created_at",)

    slug = models.SlugField("identificador", max_length=80, unique=True)
    title = models.CharField("título", max_length=200)
    description = models.TextField("descripción", blank=True)
    config = models.JSONField("configuración", default=dict, blank=True)
    is_public = models.BooleanField("visible para analistas", default=False)

    def __str__(self) -> str:
        return str(getattr(self, "título", None) or self.pk)


class KpiDefinition(TimeStampedModel, AuditedModel):
    """Indicador clave."""

    class Meta:
        verbose_name = "indicador clave"
        verbose_name_plural = "indicador claves"
        ordering = ("-created_at",)

    code = models.CharField("código", max_length=50, unique=True)
    label = models.CharField("etiqueta", max_length=200)
    unit = models.CharField("unidad", max_length=20, blank=True)
    definition = models.TextField("definición", blank=True)
    is_active = models.BooleanField("activo", default=True)

    def __str__(self) -> str:
        return str(getattr(self, "etiqueta", None) or self.pk)
