"""*uho-auth-kit* — integración con la autenticación institucional de la UHO.

Punto de entrada del paquete: reexporta el módulo ``uho_auth`` del kit y deja
una función de ayuda (:func:`kit_disponible`) para que el proyecto decida si
monta las rutas opcionales.

Documentación completa de la integración: ``docs/INTEGRACION_UHO.md``.
"""

from __future__ import annotations

from apps.integraciones.kit_uho.uho_auth import uho_login

__all__ = ["uho_login", "kit_disponible"]


def kit_disponible() -> bool:
    """``True`` si ``UHO_KIT_ENABLED=true`` en el entorno.

    Se consulta en tiempo de carga de ``config.urls`` y también desde el
    endpoint de salud/about para que la UI pueda mostrar si el kit está activo.
    """
    import os

    return os.getenv("UHO_KIT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on", "si"}
