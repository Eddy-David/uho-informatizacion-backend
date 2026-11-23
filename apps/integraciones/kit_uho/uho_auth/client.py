"""Cliente HTTP del *uho-auth-kit* contra ``auth.uho.edu.cu``.

ADAPTADO AL SIGACU (ver ``apps/integraciones/kit_uho/README.md``):

* Los valores por defecto salen del ``.env`` (``AGA_AUTH_*``) y del dict
  ``settings.UHO_INTEGRATIONS["AGA_AUTH"]``; así, cuando la UHO entregue las
  credenciales reales **solo hay que cambiar el ``.env``**, nunca este archivo
  (RNF-11).
* La respuesta se normaliza a la misma estructura que ya usa
  :class:`apps.usuarios.services.AgaAuthClient` (``username``, ``dni``,
  ``nombres``, ``apellidos``, ``tipo_usuario``, ``correo``) para que cualquier
  consumidor del SIGACU funcione sin cambios.
"""

from __future__ import annotations

import logging
import os

import requests
from django.conf import settings

logger = logging.getLogger("apps.integraciones")

#: Endpoint del servicio de autenticación institucional. Se puede sobrescribir
#: con ``AGA_AUTH_BASE_URL`` / ``AGA_AUTH_URL`` o ``UHO_AUTH_URL``.
DEFAULT_AUTH_BASE_URL = "https://auth.uho.edu.cu"
DEFAULT_AUTH_ORIGIN = "https://auth.uho.edu.cu"


def _aga_config() -> dict:
    """Configuración efectiva de AGA_AUTH, leída de los settings (que a su vez
    vienen del ``.env``)."""
    return getattr(settings, "UHO_INTEGRATIONS", {}).get("AGA_AUTH", {})


def _setting(key: str, default: str = "") -> str:
    """Lee la configuración del settings con respaldo en ``os.environ``.

    Permite usar este módulo fuera de Django (por ejemplo en un script o en
    una prueba aislada) sin romper la importación.
    """
    try:
        value = _aga_config().get(key)
    except Exception:  # pragma: no cover - settings no configurados (scripts)
        value = None
    if value:
        return str(value)
    return os.environ.get(f"AGA_AUTH_{key.upper()}", default)


def uho_login(username, password, timeout=None):
    """Valida credenciales contra ``auth.uho.edu.cu``.

    Devuelve un dict con el perfil del usuario o ``None`` si el login es
    inválido o el servicio no responde.

    El contrato de red es idéntico al que consume
    ``apps.usuarios.services.AgaAuthClient._authenticate_remote``:

    * ``POST {base_url}/login`` con cabeceras ``Origin``, ``Accept``,
      ``Content-Type`` y ``Authorization: AGA <token>``.
    * Cuerpo ``{"username", "password"}``.
    * Respuesta 200 con ``activeUser.personal_information`` y
      ``activeUser.account_info``.
    """
    base_url = (
        _setting("base_url")
        or os.environ.get("UHO_AUTH_URL", "")
        or DEFAULT_AUTH_BASE_URL
    ).rstrip("/")
    origin = _setting("origin") or os.environ.get("UHO_AUTH_ORIGIN", DEFAULT_AUTH_ORIGIN)
    api_key = (
        _setting("token")
        or os.environ.get("UHO_API_KEY", "")
    )
    if not api_key:
        raise RuntimeError(
            "Falta el token de AGA_AUTH. Defina AGA_AUTH_TOKEN (o UHO_API_KEY) "
            "en el .env; ver docs/INTEGRACION_UHO.md."
        )

    headers = {
        "Origin": origin,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"AGA {api_key}",
    }
    # El kit asumía que la URL ya incluía ``/login``; en el SIGACU
    # ``AGA_AUTH_BASE_URL`` es solo el origen, así que se normaliza aquí.
    login_url = base_url if base_url.endswith("/login") else f"{base_url}/login"

    try:
        response = requests.post(
            login_url,
            json={"username": username, "password": password},
            headers=headers,
            timeout=timeout or int(_setting("timeout", "5") or 5),
        )
        data = response.json()
    except Exception as exc:  # red, timeout, JSON inválido...
        logger.warning("Falló la consulta a auth.uho.edu.cu: %s", exc)
        return None

    if not data.get("OK") or "activeUser" not in data:
        return None

    user = data["activeUser"]
    personal = user.get("personal_information", {})
    account = user.get("account_info", {})

    return {
        "username": user.get("uid") or username,
        "name": personal.get("given_name") or personal.get("cn"),
        "surname": personal.get("sn"),
        "national_id": personal.get("dni"),
        "user_type": account.get("user_type"),
        "active": user.get("account_state") == "TRUE",
        # --- Extras que consume el SIGACU (AgaAuthClient) ---
        "dni": personal.get("dni", ""),
        "nombres": personal.get("given_name") or personal.get("cn", ""),
        "apellidos": personal.get("sn", ""),
        "tipo_usuario": account.get("user_type", "Trabajador"),
        "correo": personal.get("mail") or f"{user.get('uid') or username}@uho.edu.cu",
    }
