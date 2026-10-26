"""Solicitudes de visita y visitantes."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.constants import Campus
from apps.core.models import AuditModel, BaseModel


class VisitRequest(BaseModel, AuditModel):
    """Solicitud de entrada de un visitante (RF-05.1 – RF-05.5)."""

    class Status(models.TextChoices):
        PENDING = "PENDIENTE", "Pendiente"
        APPROVED = "APROBADA", "Aprobada"
        REJECTED = "RECHAZADA", "Rechazada"
        CHANGES = "CAMBIOS", "Cambios solicitados"
        CANCELLED = "CANCELADA", "Cancelada"
        FINISHED = "FINALIZADA", "Finalizada"

    class Meta:
        verbose_name = "solicitud de visita"
        verbose_name_plural = "solicitudes de visita"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"], name="idx_visit_request_status"),
            models.Index(fields=["-created_at"], name="idx_visit_request_created"),
        ]

    code = models.CharField("código", max_length=20, unique=True, blank=True)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="solicitante",
        on_delete=models.PROTECT,
        related_name="visit_requests",
    )
    visitor_name = models.CharField("nombre del visitante", max_length=200)
    visitor_identity_card = models.CharField("CI del visitante", max_length=11, db_index=True)
    visitor_phone = models.CharField("teléfono", max_length=30, blank=True)
    visitor_organization = models.CharField("organización", max_length=150, blank=True)
    reason = models.TextField("motivo de la visita")
    area = models.CharField("área a visitar", max_length=150)
    campus = models.CharField("sede", max_length=20, choices=Campus.choices)
    valid_from = models.DateField("válida desde")
    valid_until = models.DateField("válida hasta")
    vehicle_plate = models.CharField("placa del vehículo", max_length=20, blank=True)
    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="aprobador",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_visits",
    )
    reviewed_at = models.DateTimeField("revisada el", null=True, blank=True)
    review_comment = models.TextField("comentario de revisión", blank=True)
    attachments = models.FileField("documento adjunto", upload_to="visits/", null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.code} · {self.visitor_name}"

    @property
    def duration_days(self) -> int:
        if self.valid_from and self.valid_until:
            return (self.valid_until - self.valid_from).days + 1
        return 0

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"VIS-{timezone.now():%Y%m%d}-{self.uuid.hex[:4].upper()}"
        super().save(*args, **kwargs)

    def approve(self, reviewer, comment: str = ""):
        self.status = self.Status.APPROVED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.review_comment = comment
        self.save(
            update_fields=["status", "reviewer", "reviewed_at", "review_comment", "updated_at"]
        )
        visitor, _ = Visitor.objects.get_or_create(
            visit_request=self,
            defaults={
                "full_name": self.visitor_name,
                "identity_card": self.visitor_identity_card,
                "phone": self.visitor_phone,
                "organization": self.visitor_organization,
                "valid_from": self.valid_from,
                "valid_until": self.valid_until,
                "host_user": self.requester,
                "campus": self.campus,
                "area": self.area,
            },
        )
        return visitor

    def reject(self, reviewer, comment: str):
        self.status = self.Status.REJECTED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.review_comment = comment
        self.save(
            update_fields=["status", "reviewer", "reviewed_at", "review_comment", "updated_at"]
        )

    def request_changes(self, reviewer, comment: str):
        self.status = self.Status.CHANGES
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.review_comment = comment
        self.save(
            update_fields=["status", "reviewer", "reviewed_at", "review_comment", "updated_at"]
        )


class Visitor(BaseModel, AuditModel):
    """Visitante autorizado, con su usuario temporal y vigencia."""

    class Meta:
        verbose_name = "visitante"
        verbose_name_plural = "visitantes"
        ordering = ("-created_at",)

    visit_request = models.OneToOneField(
        VisitRequest,
        verbose_name="solicitud",
        on_delete=models.CASCADE,
        related_name="visitor",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario temporal",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="visitor_profile",
    )
    full_name = models.CharField("nombre completo", max_length=200)
    identity_card = models.CharField("CI", max_length=11, db_index=True)
    phone = models.CharField("teléfono", max_length=30, blank=True)
    organization = models.CharField("organización", max_length=150, blank=True)
    host_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="anfitrión",
        on_delete=models.PROTECT,
        related_name="hosted_visitors",
    )
    campus = models.CharField("sede", max_length=20, choices=Campus.choices)
    area = models.CharField("área", max_length=150)
    valid_from = models.DateField("válido desde")
    valid_until = models.DateField("válido hasta")
    checked_in_at = models.DateTimeField("entrada", null=True, blank=True)
    checked_out_at = models.DateTimeField("salida", null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.identity_card})"

    @property
    def is_valid(self) -> bool:
        today = timezone.localdate()
        return self.valid_from <= today <= self.valid_until
