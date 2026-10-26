"""Nomencladores compartidos: sedes, áreas, puntos de control y catálogos."""

from __future__ import annotations

from django.db import models

from apps.core.constants import RecordStatus
from apps.core.models import AuditModel, BaseModel, SoftDeleteModel


class CampusSite(BaseModel, SoftDeleteModel, AuditModel):
    """Sede física de la UHO (RF-01)."""

    class Meta:
        verbose_name = "sede"
        verbose_name_plural = "sedes"
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=["code"], name="uniq_campus_code")]

    code = models.CharField("código", max_length=30, unique=True)
    name = models.CharField("nombre", max_length=120)
    address = models.CharField("dirección", max_length=200, blank=True)
    municipality = models.CharField("municipio", max_length=80, default="Holguín")
    province = models.CharField("provincia", max_length=80, default="Holguín")
    phone = models.CharField("teléfono", max_length=30, blank=True)
    status = models.CharField(
        "estado", max_length=20, choices=RecordStatus.choices, default=RecordStatus.ACTIVE
    )

    @property
    def activo(self) -> bool:
        """Indica si la sede está operativa (alias de ``status``, RF-09.3)."""
        return self.status == RecordStatus.ACTIVE

    def __str__(self) -> str:
        return self.name


class OrganizationalUnit(BaseModel, SoftDeleteModel, AuditModel):
    """Facultad, área o dependencia administrativa."""

    class Meta:
        verbose_name = "área organizativa"
        verbose_name_plural = "áreas organizativas"
        ordering = ("name",)

    campus = models.ForeignKey(
        CampusSite,
        verbose_name="sede",
        on_delete=models.PROTECT,
        related_name="units",
    )
    name = models.CharField("nombre", max_length=150)
    acronym = models.CharField("siglas", max_length=30, blank=True)
    status = models.CharField(
        "estado", max_length=20, choices=RecordStatus.choices, default=RecordStatus.ACTIVE
    )

    @property
    def activo(self) -> bool:
        """Indica si el área está operativa (alias de ``status``, RF-09.3)."""
        return self.status == RecordStatus.ACTIVE

    def __str__(self) -> str:
        return self.name


class AccessPoint(BaseModel, SoftDeleteModel, AuditModel):
    """Punto de control (entrada peatonal o vehicular) de una sede."""

    class Meta:
        verbose_name = "punto de control"
        verbose_name_plural = "puntos de control"
        ordering = ("campus", "name")
        constraints = [models.UniqueConstraint(fields=["code"], name="uniq_access_point_code")]

    code = models.CharField("código", max_length=30, unique=True)
    name = models.CharField("nombre", max_length=120)
    campus = models.ForeignKey(CampusSite, verbose_name="sede", on_delete=models.PROTECT)
    is_vehicle_access = models.BooleanField("acceso vehicular", default=False)
    status = models.CharField(
        "estado", max_length=20, choices=RecordStatus.choices, default=RecordStatus.ACTIVE
    )

    def __str__(self) -> str:
        return f"{self.campus.name} · {self.name}"


class CatalogEntry(BaseModel, SoftDeleteModel, AuditModel):
    """Nomenclador genérico administrable (RF-08.5).

    Centraliza catálogos pequeños que no requieren modelo propio: tipos de
    vehículo, tipos de incidencia, motivos de denegación, etc.
    """

    class Kind(models.TextChoices):
        VEHICLE_TYPE = "TIPO_VEHICULO", "Tipo de vehículo"
        INCIDENT_TYPE = "TIPO_INCIDENCIA", "Tipo de incidencia"
        DENIAL_REASON = "MOTIVO_DENEGACION", "Motivo de denegación"
        VISIT_AREA = "AREA_VISITA", "Área de visita"
        ACCESS_LEVEL = "NIVEL_ACCESO", "Nivel de acceso"
        GENERIC = "GENERICO", "Genérico"

    class Meta:
        verbose_name = "entrada de nomenclador"
        verbose_name_plural = "nomencladores"
        ordering = ("kind", "sort_order", "name")
        constraints = [
            models.UniqueConstraint(fields=["kind", "code"], name="uniq_catalog_kind_code")
        ]

    kind = models.CharField("nomenclador", max_length=30, choices=Kind.choices)
    code = models.CharField("código", max_length=50)
    name = models.CharField("nombre", max_length=120)
    description = models.TextField("descripción", blank=True)
    sort_order = models.PositiveIntegerField("orden", default=0)
    is_active = models.BooleanField("activo", default=True)

    def __str__(self) -> str:
        return f"{self.get_kind_display()} · {self.name}"


class NivelAcceso(BaseModel, SoftDeleteModel, AuditModel):
    """Nivel de acceso que se imprime en el Solapín Digital (RF-09.3 / RF-03).

    Entidad propia (a diferencia de las demás entradas de ``CatalogEntry``)
    porque el solapín y la verificación de acceso la referencian por valor.
    """

    class Name(models.TextChoices):
        ACCESO_LIBRE = "ACCESO LIBRE", "Acceso libre"
        PERMANENTE = "PERMANENTE", "Permanente"
        LIMITADO = "LIMITADO", "Limitado"
        ESTUDIANTE = "ESTUDIANTE", "Estudiante"
        VISITANTE = "VISITANTE", "Visitante"

    class Meta:
        verbose_name = "nivel de acceso"
        verbose_name_plural = "niveles de acceso"
        ordering = ("sort_order", "nombre")
        constraints = [models.UniqueConstraint(fields=["nombre"], name="uniq_nivel_acceso_nombre")]

    nombre = models.CharField("nombre", max_length=30, choices=Name.choices, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    sort_order = models.PositiveIntegerField("orden", default=0)

    #: Código interno del nivel de acceso equivalente en ``AccessLevel``.
    equivalence = {
        Name.ACCESO_LIBRE: "LIBRE",
        Name.PERMANENTE: "LIBRE",
        Name.LIMITADO: "LIMITADO",
        Name.ESTUDIANTE: "ESTUDIANTE",
        Name.VISITANTE: "VISITANTE",
    }

    @property
    def codigo_acceso(self) -> str:
        """Valor de ``AccessLevel`` con el que se compara en la verificación."""
        return self.equivalence.get(self.nombre, "LIMITADO")

    def __str__(self) -> str:
        return self.get_nombre_display()
