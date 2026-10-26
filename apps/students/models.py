"""Modelos del módulo. Amplíe los campos según los requerimientos."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.audit import AuditedModel
from apps.core.models import TimeStampedModel


class StudentProfile(TimeStampedModel, AuditedModel):
    """Perfil del estudiante."""

    class Meta:
        verbose_name = "perfil del estudiante"
        verbose_name_plural = "perfil del estudiantes"
        ordering = ("-created_at",)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    student_number = models.CharField("matrícula", max_length=30, unique=True)
    career = models.CharField("carrera", max_length=150)
    faculty = models.CharField("facultad", max_length=150, blank=True)
    academic_year = models.PositiveSmallIntegerField("año académico", default=1)
    group = models.CharField("grupo", max_length=30, blank=True)
    modality = models.CharField("modalidad", max_length=40, default="CURSO_DIURNO")
    status = models.CharField("estado académico", max_length=20, default="ACTIVO")
    admitted_at = models.DateField("fecha de ingreso", null=True, blank=True)

    def __str__(self) -> str:
        return str(getattr(self, "matrícula", None) or self.pk)


class Enrollment(TimeStampedModel, AuditedModel):
    """Matrícula académica."""

    class Meta:
        verbose_name = "matrícula académica"
        verbose_name_plural = "matrícula académicas"
        ordering = ("-created_at",)

    student = models.ForeignKey(
        "students.StudentProfile",
        verbose_name="estudiante",
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        "academic.Course",
        verbose_name="asignatura",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod",
        verbose_name="período",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    status = models.CharField("estado", max_length=20, default="MATRICULADO")
    enrolled_at = models.DateField("matriculado el", null=True, blank=True)

    def __str__(self) -> str:
        return str(getattr(self, "matrícula", None) or self.pk)
