"""Modelos del módulo. Amplíe los campos según los requerimientos."""

from __future__ import annotations

from django.db import models

from apps.core.audit import AuditedModel
from apps.core.models import TimeStampedModel


class AcademicPeriod(TimeStampedModel, AuditedModel):
    """Período docente."""

    class Meta:
        verbose_name = "período docente"
        verbose_name_plural = "período docentes"
        ordering = ("-created_at",)

    code = models.CharField("código", max_length=30, unique=True)
    name = models.CharField("nombre", max_length=150)
    kind = models.CharField("tipo", max_length=20, default="SEMESTRE")
    start_date = models.DateField("inicio")
    end_date = models.DateField("fin")
    is_active = models.BooleanField("activo", default=True)

    def __str__(self) -> str:
        return str(getattr(self, "código", None) or self.pk)


class Course(TimeStampedModel, AuditedModel):
    """Asignatura."""

    class Meta:
        verbose_name = "asignatura"
        verbose_name_plural = "asignaturas"
        ordering = ("-created_at",)

    code = models.CharField("código", max_length=30, unique=True)
    name = models.CharField("nombre", max_length=200)
    credits = models.PositiveSmallIntegerField("créditos", default=0)
    semester = models.PositiveSmallIntegerField("semestre", default=1)
    is_active = models.BooleanField("activa", default=True)

    def __str__(self) -> str:
        return str(getattr(self, "código", None) or self.pk)


class GradeRecord(TimeStampedModel, AuditedModel):
    """Registro de calificación."""

    class Meta:
        verbose_name = "registro de calificación"
        verbose_name_plural = "registro de calificacións"
        ordering = ("-created_at",)

    enrollment = models.ForeignKey(
        "students.Enrollment",
        verbose_name="matrícula",
        on_delete=models.CASCADE,
        related_name="grades",
    )
    evaluation = models.CharField("evaluación", max_length=80)
    score = models.DecimalField("nota", max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField("estado", max_length=20, default="REGISTRADA")
    evaluated_at = models.DateField("evaluado el", null=True, blank=True)

    def __str__(self) -> str:
        return str(getattr(self, "evaluación", None) or self.pk)
