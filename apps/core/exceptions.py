"""Manejador de excepciones uniforme para toda la API.

Todas las respuestas de error comparten la misma estructura::

    {
        "error": {
            "code": "validation_error",
            "message": "Los datos enviados no son válidos.",
            "details": {"campo": ["mensaje"]}
        }
    }
"""

from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("apps.core")


def _error_payload(code: str, message: str, details=None, status_code: int = 400) -> Response:
    return Response(
        {"error": {"code": code, "message": message, "details": details, "status": status_code}},
        status=status_code,
    )


def api_exception_handler(exc, context):
    """Normaliza las excepciones de DRF y Django en una única estructura."""
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(
            exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        )
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)

    if response is not None:
        code = getattr(getattr(exc, "detail", None), "code", "error")
        message = response.data.get("detail") if isinstance(response.data, dict) else None
        details = None if message else response.data
        return _error_payload(
            code=str(code),
            message=str(message) if message else "No se pudo procesar la solicitud.",
            details=details,
            status_code=response.status_code,
        )

    if isinstance(exc, IntegrityError):
        logger.warning("Violación de integridad: %s", exc)
        return _error_payload(
            "integrity_error",
            "La operación entra en conflicto con datos existentes.",
            status_code=status.HTTP_409_CONFLICT,
        )

    logger.exception("Excepción no controlada en la API", exc_info=exc)
    return _error_payload(
        "server_error",
        "Ocurrió un error inesperado. Contacte al administrador del sistema.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
