"""Modelos base reutilizables en todas las aplicaciones."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """Añade un identificador público (UUID) además de la PK autoincremental."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Marcas de creación/actualización gestionadas automáticamente."""

    created_at = models.DateTimeField("creado el", default=timezone.now, editable=False)
    updated_at = models.DateTimeField("actualizado el", auto_now=True, editable=False)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet que excluye por defecto los registros "eliminados"."""

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)
    def restore(self):
        return self.update(is_deleted=False, deleted_at=None)

    def delete(self):  # noqa: D401 - sobreescritura intencional
        return self.update(is_deleted=True, deleted_at=timezone.now())


class SoftDeleteManager(models.Manager):
    """Manager por defecto que oculta registros eliminados lógicamente."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """Manager para consultar también los registros eliminados."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    """Eliminación lógica: la información nunca se borra físicamente."""

    is_deleted = models.BooleanField("eliminado", default=False, db_index=True)
    deleted_at = models.DateTimeField("eliminado el", null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)
    def restore(self):
        """Recupera un registro previamente "eliminado" lógicamente."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])
        return self


class BaseModel(UUIDModel, TimeStampedModel):
    """Combinación habitual: UUID público + marcas temporales."""

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class AuditModel(models.Model):
    """Trazabilidad de quién creó y modificó un registro (RF-08)."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creado por",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="actualizado por",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Nomencladores compartidos
# ---------------------------------------------------------------------------
# Django solo registra los modelos definidos en ``models.py`` (o importados
# desde él). Los nomencladores viven en ``catalogs.py`` por motivos de
# organización, por lo que se importan aquí para que formen parte del registro
# de modelos de la aplicación ``core``.
from apps.core.catalogs import (  # noqa: E402,F401
    AccessPoint,
    CampusSite,
    CatalogEntry,
    NivelAcceso,
    OrganizationalUnit,
)
