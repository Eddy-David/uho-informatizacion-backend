"""Servicios del Solapín Digital (RF-03).

Centraliza las reglas de negocio que no dependen de la petición HTTP:

* ``nivel_acceso_por_defecto`` → tabla de RF-03.7.
* ``generar_solapin``          → emite (o reutiliza) el solapín de un usuario.
"""

from __future__ import annotations

import logging

from django.db import models, transaction

from apps.core.audit import AuditEvent, audit_event
from apps.core.constants import AccessLevel, UserType
from apps.solapines.models import Badge, BadgeTemplate

logger = logging.getLogger("apps.solapines")

#: Nivel de acceso por defecto según el tipo de usuario (RF-03.7).
NIVEL_POR_TIPO_USUARIO = {
    UserType.MANAGER: AccessLevel.FREE,  # Cuadro / Directivo → ACCESO LIBRE
    UserType.TEACHER: AccessLevel.PERMANENT,  # Profesor → ACCESO PERMANENTE
    UserType.WORKER: AccessLevel.LIMITED,  # Trabajador → ACCESO LIMITADO
    UserType.STUDENT: AccessLevel.STUDENT,  # Estudiante → ESTUDIANTE
    UserType.VISITOR: AccessLevel.VISITOR,  # Visitante → VISITANTE (temporal)
}


def nivel_acceso_por_defecto(user_type: str) -> str:
    """Devuelve el nivel de acceso que corresponde a un tipo de usuario."""
    return NIVEL_POR_TIPO_USUARIO.get(user_type, AccessLevel.LIMITED)


def plantilla_para(user_type: str) -> BadgeTemplate | None:
    """Plantilla por defecto del tipo de usuario (None si aún no existe)."""
    return (
        BadgeTemplate.objects.filter(is_default=True, user_type=user_type).first()
        or BadgeTemplate.objects.filter(is_default=True).first()
    )


@transaction.atomic
def generar_solapin(usuario) -> tuple[Badge, bool]:
    """Emite el Solapín Digital de ``usuario`` aplicando la regla RF-03.7.

    Si el usuario ya tiene un solapín activo se devuelve tal cual, de modo que
    la operación es idempotente (necesario para ``GET my-solapin``).

    :returns: tupla ``(solapin, creado)``.
    """
    existente = (
        Badge.objects.select_related("user", "template")
        .filter(user=usuario, status=Badge.Status.ACTIVE)
        .first()
    )
    if existente is not None:
        return existente, False

    # La restricción única sobre el solapín activo no excluye los registros
    # borrados lógicamente: se eliminan físicamente para poder emitir uno nuevo.
    # ``SoftDeleteQuerySet.delete()`` sólo marca is_deleted, por eso se usa SQL.
    models.QuerySet.delete(Badge.all_objects.filter(user=usuario, is_deleted=True))

    nivel = nivel_acceso_por_defecto(usuario.tipo_usuario)
    badge = Badge.objects.create(
        user=usuario,
        template=plantilla_para(usuario.tipo_usuario),
        access_level=nivel,
        status=Badge.Status.ACTIVE,
    )
    # Se sincroniza el nivel del perfil para que el resto del sistema lo vea.
    if usuario.nivel_acceso != nivel:
        usuario.nivel_acceso = nivel
        usuario.save(update_fields=["nivel_acceso"])

    audit_event(
        action=AuditEvent.Action.CREATE,
        module="solapines",
        actor=usuario,
        target=badge,
        description=f"Solapín generado con nivel {nivel} (RF-03.7).",
        metadata={"codigo_qr": str(badge.codigo_qr), "nivel_acceso": nivel},
    )
    logger.info("Solapín %s creado para %s con nivel %s", badge.badge_number, usuario, nivel)
    return badge, True
