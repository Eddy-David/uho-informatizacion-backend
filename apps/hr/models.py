"""Modelos del módulo. Amplíe los campos según los requerimientos."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.audit import AuditedModel
from apps.core.models import TimeStampedModel


class Position(TimeStampedModel, AuditedModel):
    """Cargo."""

    class Meta:
        verbose_name = "cargo"
        verbose_name_plural = "cargos"
        ordering = ("-created_at",)

    code = models.CharField("código", max_length=30, unique=True)
    name = models.CharField("nombre", max_length=150)
    category = models.CharField("categoría", max_length=80, blank=True)
    is_teaching = models.BooleanField("docente", default=False)

    def __str__(self) -> str:
        return str(getattr(self, "nombre", None) or self.pk)


class EmployeeRecord(TimeStampedModel, AuditedModel):
    """Expediente laboral."""

    class Meta:
        verbose_name = "expediente laboral"
        verbose_name_plural = "expediente laborals"
        ordering = ("-created_at",)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.CASCADE,
        related_name="employee_record",
    )
    employee_number = models.CharField("expediente", max_length=30, unique=True)
    position = models.ForeignKey(
        "hr.Position",
        verbose_name="cargo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employees",
    )
    department = models.CharField("departamento", max_length=150, blank=True)
    hired_at = models.DateField("fecha de alta", null=True, blank=True)
    contract_type = models.CharField("tipo de contrato", max_length=40, default="INDEFINIDO")
    status = models.CharField("estado", max_length=20, default="ACTIVO")

    def __str__(self) -> str:
        return str(getattr(self, "número de expediente", None) or self.pk)


class LeaveRequest(TimeStampedModel, AuditedModel):
    """Solicitud de ausencia."""

    class Meta:
        verbose_name = "solicitud de ausencia"
        verbose_name_plural = "solicitud de ausencias"
        ordering = ("-created_at",)

    employee = models.ForeignKey(
        "hr.EmployeeRecord",
        verbose_name="empleado",
        on_delete=models.CASCADE,
        related_name="leaves",
    )
    kind = models.CharField("tipo", max_length=30, default="VACACIONES")
    start_date = models.DateField("desde")
    end_date = models.DateField("hasta")
    status = models.CharField("estado", max_length=20, default="PENDIENTE")
    reason = models.TextField("motivo", blank=True)

    def __str__(self) -> str:
        return str(getattr(self, "tipo", None) or self.pk)
