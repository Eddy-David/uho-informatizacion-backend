"""Módulo ``uho_auth`` del *uho-auth-kit* integrado en el SIGACU.

Contenido (ver ``docs/INTEGRACION_UHO.md``):

* :func:`client.uho_login` — validación de credenciales contra
  ``auth.uho.edu.cu`` (AGA_AUTH).
* :class:`views.KitLoginView` / :class:`views.KitLogoutView` — login/logout con
  Token DRF, **opcionales** (``UHO_KIT_ENABLED=true``).

La integración activa del SIGACU sigue siendo ``apps.usuarios.services.
AgaAuthClient`` (JWT + ``AGA_AUTH_MODE``); este paquete existe para aprovechar
el kit institucional sin acoplar el dominio al proveedor.
"""

from .client import uho_login  # noqa: F401
