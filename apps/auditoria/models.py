"""Modelo de registro de auditoría (Sección 6 de requisitos.md)."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class LogAuditoria(models.Model):
    """Registro inmutable de acciones relevantes realizadas en el sistema."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registros_auditoria",
    )
    modulo = models.CharField("módulo", max_length=100)
    accion = models.CharField("acción", max_length=100)
    detalle = models.JSONField("detalle", default=dict, blank=True)
    fecha_hora = models.DateTimeField("fecha y hora", auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField("dirección IP", null=True, blank=True)
    user_agent = models.CharField("agente de usuario", max_length=300, blank=True)
    request_id = models.CharField("ID de petición", max_length=64, blank=True, db_index=True)
    method = models.CharField("método HTTP", max_length=10, blank=True)
    ruta = models.CharField("ruta", max_length=255, blank=True)
    status_code = models.PositiveSmallIntegerField("código HTTP", null=True, blank=True)

    class Meta:
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"
        ordering = ("-fecha_hora",)
        indexes = [
            models.Index(fields=["modulo", "-fecha_hora"], name="idx_logaud_modulo"),
            models.Index(fields=["usuario", "-fecha_hora"], name="idx_logaud_usuario"),
        ]

    def __str__(self):
        user = str(self.usuario) if self.usuario_id else "anónimo"
        return f"{self.fecha_hora:%Y-%m-%d %H:%M} — {user} — {self.modulo}:{self.accion}"

    def save(self, *args, **kwargs):
        """Registro inmutable: solo se permite la creación."""
        if self.pk is not None:
            raise ValueError("Los registros de auditoría no se pueden modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Los registros de auditoría no se pueden eliminar.")
