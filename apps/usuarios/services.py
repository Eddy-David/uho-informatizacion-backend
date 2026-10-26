"""Servicios de integración con sistemas externos (AGA_AUTH, SIGENU...).

``AgaAuthClient`` centraliza la autenticación contra AGA_AUTH. En modo MOCK
(activado con ``AGA_AUTH_MODE=mock``, el valor por defecto en desarrollo)
devuelve datos simulados sin contactar ningún servicio real. Cuando exista
el servicio institucional, se implementará ``_authenticate_remote`` con las
credenciales reales y el mismo contrato de respuesta.
"""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger("apps.usuarios")

#: Mapeo del tipo de usuario devuelto por AGA_AUTH a ``UserType`` local.
TIPO_USUARIO_MAP = {
    "Estudiante": "ESTUDIANTE",
    "Profesor": "PROFESOR",
    "Trabajador": "TRABAJADOR",
    "Cuadro": "CUADRO",
    "Visitante": "VISITANTE",
}


class AgaAuthError(Exception):
    """AGA_AUTH rechazó las credenciales o el servicio no está disponible."""


class AgaAuthClient:
    """Cliente de autenticación centralizada AGA_AUTH (modo MOCK por defecto)."""

    def __init__(self, mode: str | None = None):
        self.mode = (mode or getattr(settings, "AGA_AUTH_MODE", "mock")).lower()

    # ------------------------------------------------------------------
    def authenticate(self, username: str, password: str) -> dict:
        """Valida las credenciales y devuelve el perfil del usuario.

        :raises AgaAuthError: si las credenciales no son válidas.
        """
        username = (username or "").strip().lower()
        if not username or not password:
            raise AgaAuthError("Usuario y contraseña son obligatorios.")

        if self.mode == "mock":
            logger.warning(
                "AGA_AUTH en modo MOCK: las credenciales NO se validan de verdad. "
                "No use este modo en producción (AGA_AUTH_MODE=real)."
            )
            return self._authenticate_mock(username, password)
        return self._authenticate_remote(username, password)

    # ------------------------------------------------------------------
    def _authenticate_mock(self, username: str, password: str) -> dict:
        """Simulación: acepta cualquier contraseña no vacía (solo desarrollo).

        La protección de producción está en que el despliegue configure
        ``AGA_AUTH_MODE=real``; en mock se emite una advertencia en los logs.
        """
        perfil = {
            "username": username,
            "dni": "91050612345",
            "nombres": "Nombre Simulado",
            "apellidos": "Apellido Simulado",
            "tipo_usuario": "Trabajador",
            "correo": f"{username}@uho.edu.cu",
        }
        logger.info("AGA_AUTH (mock) autenticó a %s", username)
        return perfil

    def _authenticate_remote(self, username: str, password: str) -> dict:
        """Valida las credenciales contra AGA_AUTH (requisitos §9, RF-01.1/01.2).

        Contrato: ``POST {base_url}/login`` con cabeceras Origin, Accept,
        Content-Type y el token ``Authorization: AGA <token>``; el cuerpo lleva
        ``{"username", "password"}``. La respuesta 200 incluye
        ``activeUser.personal_information`` y ``activeUser.account_info``.

        :raises AgaAuthError: en 401 (credenciales), 409 (formato), 500 (servidor)
            o si el servicio no responde dentro del tiempo configurado.
        """
        import requests
        config = getattr(settings, "UHO_INTEGRATIONS", {}).get("AGA_AUTH", {})
        base_url = (config.get("base_url") or "").rstrip("/")
        if not base_url:
            raise AgaAuthError("AGA_AUTH no tiene URL configurada (AGA_AUTH_BASE_URL).")
        token = config.get("token") or getattr(settings, "AGA_AUTH_TOKEN", "")
        headers = {
            "Origin": config.get("origin") or getattr(settings, "AGA_AUTH_ORIGIN", ""),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"AGA {token}".strip(),
        }
        try:
            response = requests.post(
                f"{base_url}/login",
                json={"username": username, "password": password},
                headers=headers,
                timeout=config.get("timeout", 5),
            )
        except requests.RequestException as exc:
            logger.error("AGA_AUTH no respondió para %s: %s", username, exc)
            raise AgaAuthError("El servicio de autenticación no está disponible.") from exc
        # RF-01.2: interpretación explícita de los códigos del contrato.
        if response.status_code == 401:
            raise AgaAuthError("Usuario o contraseña incorrectos.")
        if response.status_code == 409:
            raise AgaAuthError("El formato de la solicitud no es válido.")
        if response.status_code >= 500:
            raise AgaAuthError("Error interno del servicio de autenticación.")
        if response.status_code != 200:
            raise AgaAuthError("AGA_AUTH devolvió un estado inesperado.")
        try:
            active_user = response.json()["activeUser"]
            personal = active_user["personal_information"]
            account = active_user["account_info"]
        except (KeyError, TypeError, ValueError) as exc:
            raise AgaAuthError("Respuesta de AGA_AUTH con formato inválido.") from exc
        return {
            "username": username,
            "dni": personal.get("dni", ""),
            "nombres": personal.get("given_name") or personal.get("cn", ""),
            "apellidos": personal.get("sn", ""),
            "tipo_usuario": account.get("user_type", "Trabajador"),
            "correo": personal.get("mail") or f"{username}@uho.edu.cu",
        }

    def logout(self) -> None:
        """Notifica el cierre de sesión a AGA_AUTH (RF-01.5).

        La sesión local ya quedó invalidada por el llamador: un fallo de red
        aquí solo se registra, nunca revierte el cierre de sesión.
        """
        if self.mode != "real":
            return
        import requests
        config = getattr(settings, "UHO_INTEGRATIONS", {}).get("AGA_AUTH", {})
        base_url = (config.get("base_url") or "").rstrip("/")
        if not base_url:
            return
        token = config.get("token") or getattr(settings, "AGA_AUTH_TOKEN", "")
        try:
            requests.post(
                f"{base_url}/logout",
                headers={"Accept": "application/json", "Authorization": f"AGA {token}".strip()},
                timeout=config.get("timeout", 5),
            )
        except requests.RequestException as exc:
            logger.warning("No se pudo notificar el logout a AGA_AUTH: %s", exc)
