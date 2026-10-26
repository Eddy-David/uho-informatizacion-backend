"""Plantillas y credenciales del Solapín Digital."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.constants import AccessLevel, Campus, RecordStatus, UserType
from apps.core.models import AuditModel, BaseModel, SoftDeleteModel
from apps.core.utils import generate_qr_token, qr_payload


class BadgeTemplate(BaseModel, SoftDeleteModel, AuditModel):
    """Imagen base del Solapín y definición de sus zonas dinámicas (RF-03.1)."""

    class Meta:
        verbose_name = "plantilla de solapín"
        verbose_name_plural = "plantillas de solapín"
        ordering = ("-is_default", "name")

    name = models.CharField("nombre", max_length=120)
    user_type = models.CharField(
        "tipo de usuario", max_length=20, choices=UserType.choices, default=UserType.STUDENT
    )
    campus = models.CharField("sede", max_length=20, choices=Campus.choices, blank=True)
    background_image = models.ImageField(
        "imagen base", upload_to="badges/templates/", null=True, blank=True
    )
    primary_color = models.CharField("color primario", max_length=9, default="#14305C")
    secondary_color = models.CharField("color secundario", max_length=9, default="#D9A441")
    # Zonas dinámicas en porcentaje del ancho/alto de la plantilla:
    # {"photo": {"x": 6, "y": 18, "w": 30, "h": 34}, "qr": {...}, "name": {...}}
    zones = models.JSONField("zonas dinámicas", default=dict, blank=True)
    is_default = models.BooleanField("plantilla por defecto", default=False)
    status = models.CharField(
        "estado", max_length=20, choices=RecordStatus.choices, default=RecordStatus.ACTIVE
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.get_user_type_display()})"

    def save(self, *args, **kwargs):
        if self.is_default:
            BadgeTemplate.objects.filter(user_type=self.user_type, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)


class Badge(BaseModel, SoftDeleteModel, AuditModel):
    """Credencial digital asignada a un usuario del campus (RF-02)."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVO", "Activo"
        SUSPENDED = "SUSPENDIDO", "Suspendido"
        CANCELLED = "CANCELADO", "Cancelado"
        EXPIRED = "VENCIDO", "Vencido"

    class Meta:
        verbose_name = "solapín"
        verbose_name_plural = "solapines"
        ordering = ("-issued_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="ACTIVO"),
                name="uniq_active_badge_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["qr_token"], name="idx_badge_qr_token"),
            models.Index(fields=["status"], name="idx_badge_status"),
        ]

    badge_number = models.CharField("número de solapín", max_length=30, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.PROTECT,
        related_name="badges",
    )
    template = models.ForeignKey(
        BadgeTemplate,
        verbose_name="plantilla",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="badges",
    )
    access_level = models.CharField(
        "nivel de acceso", max_length=20, choices=AccessLevel.choices, default=AccessLevel.LIMITED
    )
    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    qr_token = models.CharField("token QR", max_length=64, unique=True, default=generate_qr_token)
    #: Identificador público que se codifica en el QR (RF-03 / RF-03.9).
    #: El QR contiene únicamente este UUID y el estado: nunca datos personales.
    codigo_qr = models.UUIDField(
        "código QR", default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    issued_at = models.DateTimeField("expedido el", default=timezone.now)
    expires_at = models.DateTimeField("vence el", null=True, blank=True)
    valid_from = models.DateField("válido desde", null=True, blank=True)
    valid_until = models.DateField("válido hasta", null=True, blank=True)
    notes = models.TextField("observaciones", blank=True)

    def __str__(self) -> str:
        return f"{self.badge_number} · {self.user.nombre_completo}"

    @property
    def is_valid(self) -> bool:
        now = timezone.now()
        if self.status != self.Status.ACTIVE:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        if self.valid_until and self.valid_until < now.date():
            return False
        return True

    def cancel(self, reason: str = "", applied_by=None):
        self.status = self.Status.CANCELLED
        self.notes = (self.notes + f"\nCancelado: {reason}").strip()
        if applied_by is not None:
            self.updated_by = applied_by
        self.save(update_fields=["status", "notes", "updated_by", "updated_at"])

    def renew(self, days: int = 365):
        self.status = self.Status.ACTIVE
        self.issued_at = timezone.now()
        self.expires_at = timezone.now() + timezone.timedelta(days=days)
        self.qr_token = generate_qr_token()
        self.save(update_fields=["status", "issued_at", "expires_at", "qr_token", "updated_at"])
        return self

    def rotate_qr(self) -> str:
        """Regenera el token QR (útil si el solapín se extravió)."""
        self.qr_token = generate_qr_token()
        self.codigo_qr = uuid.uuid4()
        self.save(update_fields=["qr_token", "codigo_qr", "updated_at"])
        return self.qr_token

    @property
    def qr_payload(self) -> str:
        """Contenido del QR: sólo UUID + estado (RF-03.9, sin datos personales)."""
        return qr_payload(self.codigo_qr, self.status)

    def save(self, *args, **kwargs):
        if not self.badge_number:
            year = timezone.now().year
            self.badge_number = f"UHO-{year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class BadgePrintJob(BaseModel, AuditModel):
    """Cola de impresión masiva de solapines por sede, área y tipo de usuario."""

    class Status(models.TextChoices):
        PENDING = "PENDIENTE", "Pendiente"
        PROCESSING = "PROCESANDO", "Procesando"
        DONE = "LISTO", "Listo"
        FAILED = "ERROR", "Error"

    class Meta:
        verbose_name = "lote de impresión"
        verbose_name_plural = "lotes de impresión"
        ordering = ("-created_at",)

    campus = models.CharField("sede", max_length=20, choices=Campus.choices, blank=True)
    area = models.CharField("área", max_length=150, blank=True)
    user_type = models.CharField(
        "tipo de usuario", max_length=20, choices=UserType.choices, blank=True
    )
    total = models.PositiveIntegerField("total", default=0, validators=[MinValueValidator(0)])
    processed = models.PositiveIntegerField("procesados", default=0)
    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    file = models.FileField("archivo generado", upload_to="badges/print/", null=True, blank=True)
    error_message = models.TextField("mensaje de error", blank=True)

    def __str__(self) -> str:
        return f"Lote {self.uuid} · {self.status}"
