"""
Middlewares transversales del SIGACU.

* ``RequestAuditMiddleware`` → asigna un ID de correlación, mide la duración,
  registra peticiones de escritura exitosas y deja el contexto (usuario, IP,
  request) disponible para la auditoría.
* ``SecurityHeadersMiddleware`` → cabeceras de endurecimiento adicionales.
"""

from __future__ import annotations

import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject

import json

from apps.core.audit import AuditEvent, audit_context, audit_event
from apps.core.utils import client_ip

logger = logging.getLogger("apps.request")

#: Claves del cuerpo de la petición que nunca se guardan en el log.
SENSITIVE_KEYS = {
    "password",
    "password1",
    "password2",
    "old_password",
    "new_password",
    "confirm_password",
    "token",
    "access",
    "refresh",
    "secret",
    "api_key",
}

#: Rutas que no se auditan automáticamente (ruido o alto volumen).
IGNORED_PATHS = (
    "/api/v1/health/",
    "/api/v1/notifications/unread_count/",
    "/static/",
    "/media/",
    "/favicon",
)

#: Rutas monitorizadas pero sin evento de auditoría por cada petición.
MONITOR_ONLY_PATHS = (
    "/api/v1/access/verify/",
    "/api/v1/access_control/verify/",
    "/api/v1/solapines/verify/",
)


class RequestAuditMiddleware(MiddlewareMixin):
    """Contexto de auditoría + trazas de peticiones."""

    def process_request(self, request):
        request.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request._audit_start = time.perf_counter()
        # El cuerpo se lee aquí, antes de que DRF lo consuma al parsear la vista.
        # Tras el parseo, ``request.body`` lanza ``RawPostDataException``.
        request._audit_cached_body = _read_body(request)

        def _user():
            return getattr(request, "user", None)

        context = audit_context(
            request=SimpleLazyObject(lambda: request),
            request_id=request.request_id,
            user=SimpleLazyObject(_user),
        )
        context.__enter__()
        request._audit_context_manager = context
        return None

    def process_response(self, request, response):
        # La auditoría se escribe ANTES de cerrar el contexto: así ``current_user()``
        # sigue disponible y el LogAuditoria queda vinculado al usuario real.
        start = getattr(request, "_audit_start", None)
        duration_ms = int((time.perf_counter() - start) * 1000) if start else None
        response["X-Request-ID"] = getattr(request, "request_id", "")

        try:
            self._maybe_audit(request, response, duration_ms)
        except Exception:  # pragma: no cover - nunca rompe la respuesta
            logger.exception("Fallo al auditar la petición %s", request.path)
        finally:
            context = getattr(request, "_audit_context_manager", None)
            if context is not None:
                context.__exit__(None, None, None)

        if duration_ms is not None and duration_ms > 2000:
            logger.warning(
                "Petición lenta: %s %s %sms (req=%s)",
                request.method,
                request.path,
                duration_ms,
                getattr(request, "request_id", ""),
            )
        return response

    def process_exception(self, request, exception):
        context = getattr(request, "_audit_context_manager", None)
        if context is not None:
            context.__exit__(type(exception), exception, exception.__traceback__)
        return None

    @staticmethod
    def _maybe_audit(request, response, duration_ms):
        path = request.path or ""
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return
        if any(path.startswith(prefix) for prefix in IGNORED_PATHS):
            return
        if any(path.startswith(prefix) for prefix in MONITOR_ONLY_PATHS):
            return
        if 400 <= response.status_code < 500:
            # Los rechazos se registran como advertencia (posible intento de abuso).
            audit_event(
                action=AuditEvent.Action.OTHER,
                module="api",
                description=f"{request.method} {path} rechazado",
                metadata={"status": response.status_code, "duracion_ms": duration_ms},
                severity=AuditEvent.Severity.WARNING,
                request=request,
            )
        elif response.status_code < 500:
            audit_event(
                action=AuditEvent.Action.OTHER,
                module="api",
                description=f"{request.method} {path}",
                metadata={"status": response.status_code, "duracion_ms": duration_ms},
                request=request,
            )
        # Registro unificado en LogAuditoria (Sección 6 de requisitos.md):
        # misma política de ruido, usuario, IP y estado que AuditEvent.
        _log_auditoria(request, response, duration_ms)


def _read_body(request):
    """Devuelve el cuerpo crudo sin fallar si el stream ya fue consumido."""
    try:
        return request.body
    except Exception:  # RawPostDataException: DRF ya leyó el stream.
        inner = getattr(request, "_request", None)
        return getattr(inner, "_body", b"") if inner is not None else b""


def _sanitize(data):
    """Devuelve una copia del cuerpo sin información sensible."""
    if isinstance(data, list):
        return [_sanitize(item) for item in data]
    if not isinstance(data, dict):
        return data
    clean = {}
    for key, value in data.items():
        if str(key).lower() in SENSITIVE_KEYS:
            clean[key] = "***"
        elif isinstance(value, (dict, list)):
            clean[key] = _sanitize(value)
        else:
            clean[key] = value
    return clean


def _log_auditoria(request, response, duration_ms):
    """Guarda la petición de escritura en LogAuditoria (nunca rompe la respuesta)."""
    try:
        from apps.auditoria.models import LogAuditoria
        from apps.core.audit import current_user

        user = current_user()
        if user is None:
            # Respaldo: el contexto puede no estar inicializado (p. ej. en pruebas
            # directas o middlewares de terceros que llamen a _maybe_audit), o el
            # login acaba de autenticar y el usuario no existía al entrar: en ese
            # caso DRF deja ``request.user`` disponible al volver de la vista.
            user = getattr(request, "user", None)
        if user is not None and not getattr(user, "is_authenticated", False):
            user = None

        detalle = {
            "metodo": request.method,
            "status": response.status_code,
        }
        if duration_ms is not None:
            detalle["duracion_ms"] = duration_ms

        body = getattr(request, "_audit_cached_body", None)
        if body is None:
            body = _read_body(request)
        if body:
            try:
                detalle["cuerpo"] = _sanitize(json.loads(body.decode("utf-8")))
            except (ValueError, UnicodeDecodeError, AttributeError):
                detalle["cuerpo"] = "<no-JSON>"

        LogAuditoria.objects.create(
            usuario=user,
            modulo=(request.path.strip("/").split("/") or ["api"])[0],
            accion=request.method,
            detalle=detalle,
            ip_address=client_ip(request) or None,
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:300],
            request_id=getattr(request, "request_id", ""),
            method=request.method,
            ruta=(request.path or "")[:255],
            status_code=response.status_code,
        )
    except Exception:
        logger.exception("Fallo al registrar LogAuditoria de %s %s", request.method, request.path)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Cabeceras de seguridad coherentes con la política institucional."""

    def process_response(self, request, response):
        response.setdefault("Referrer-Policy", "same-origin")
        response.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
        if not response.has_header("Content-Security-Policy") and hasattr(response, "content"):
            response["X-Content-Type-Options"] = "nosniff"
        return response
