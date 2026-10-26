"""Modelos del módulo. Amplíe los campos según los requerimientos."""

from __future__ import annotations

from django.db import models

from apps.core.audit import AuditedModel
from apps.core.models import TimeStampedModel


class ResearchProject(TimeStampedModel, AuditedModel):
    """Proyecto de investigación."""

    class Meta:
        verbose_name = "proyecto de investigación"
        verbose_name_plural = "proyecto de investigacións"
        ordering = ("-created_at",)

    code = models.CharField("código", max_length=30, unique=True)
    title = models.CharField("título", max_length=250)
    leader = models.CharField("jefe de proyecto", max_length=150, blank=True)
    area = models.CharField("línea de investigación", max_length=150, blank=True)
    funding = models.DecimalField(
        "financiamiento", max_digits=12, decimal_places=2, null=True, blank=True
    )
    start_date = models.DateField("inicio", null=True, blank=True)
    end_date = models.DateField("fin", null=True, blank=True)
    status = models.CharField("estado", max_length=20, default="EN_CURSO")

    def __str__(self) -> str:
        return str(getattr(self, "título", None) or self.pk)


class ProjectMilestone(TimeStampedModel, AuditedModel):
    """Hito del proyecto."""

    class Meta:
        verbose_name = "hito del proyecto"
        verbose_name_plural = "hito del proyectos"
        ordering = ("-created_at",)

    project = models.ForeignKey(
        "research.ResearchProject",
        verbose_name="proyecto",
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    title = models.CharField("título", max_length=200)
    due_date = models.DateField("fecha prevista", null=True, blank=True)
    status = models.CharField("estado", max_length=20, default="PENDIENTE")

    def __str__(self) -> str:
        return str(getattr(self, "título", None) or self.pk)
