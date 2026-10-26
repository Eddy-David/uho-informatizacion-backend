"""Reglas de negocio del módulo Mantenimiento.

Concentre aquí la lógica de dominio. Las vistas deben limitarse a validar
entrada, invocar el servicio y serializar la respuesta.

Ejemplo::

    def approve(instance, actor, comment=""):
        ...
        audit_event(action="APPROVE", module=MODULE, target=instance, actor=actor)
"""

from __future__ import annotations

from apps.core.audit import AuditEvent, audit_event

MODULE = "maintenance"


def record_event(action: str, description: str, target=None, actor=None, **metadata) -> None:
    """Atajo local para auditar acciones del módulo."""
    audit_event(
        action=action,
        module=MODULE,
        description=description,
        target=target,
        actor=actor,
        metadata=metadata,
    )


__all__ = ["MODULE", "record_event", "AuditEvent"]
