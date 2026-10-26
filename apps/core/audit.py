"""
Auditoría empresarial transversal del SIGACU.

Registra **quién hizo qué, cuándo, desde dónde y con qué resultado** sobre las
entidades del sistema:

* ``AuditEvent``        → modelo inmutable (append-only) de eventos.
* ``AuditMiddleware``   → identifica actor/IP/dispositivo de cada petición.
* ``track_signals``     → señales ``post_save``/``post_delete`` de las apps auditadas.
* ``audit_event()``     → registro explícito desde servicios de negocio.
* ``audit_action()``    → decorador para acciones puntuales (exportaciones, aprobaciones).
* ``AuditedModel``      → mixin marcador que activa la auditoría automática.

Buenas prácticas aplicadas:

1. **No bloquea el negocio**: cualquier fallo al auditar se registra en el log y
   se ignora (excepto en ``audit_event`` explícito con ``strict=True``).
2. **Datos mínimos**: se guardan diferencias de campos, nunca contraseñas ni
   contenido de archivos.
3. **Inmutabilidad**: los eventos no se editan ni se borran desde la API.
4. **Retención**: ``python manage.py purge_audit --days 730``.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

logger = logging.getLogger("apps.audit")

#: Campos que nunca se incluyen en las diferencias auditadas.
SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "last_login",
        "token",
        "refresh",
        "access",
        "secret",
        "secret_key",
        "api_key",
        "qr_token",
    }
)

#: Apps cuyos modelos se auditan automáticamente (evita ruido de tablas técnicas).
AUDITED_APPS = frozenset(
    {
        "usuarios",
        "access_control",
        "solapines",
        "visitors",
        "vehicles",
        "incidents",
        "core",
    }
)


class AuditEvent(models.Model):
    """Evento de auditoría inmutable."""

    class Action(models.TextChoices):
        CREATE = "CREATE", "Creación"
        UPDATE = "UPDATE", "Modificación"
        DELETE = "DELETE", "Eliminación"
        LOGIN_SUCCESS = "LOGIN_SUCCESS", "Inicio de sesión exitoso"
        LOGIN_FAILED = "LOGIN_FAILED", "Intento fallido de autenticación"
        LOGOUT = "LOGOUT", "Cierre de sesión"
        VERIFY_ACCESS = "VERIFY_ACCESS", "Verificación de acceso"
        APPROVE = "APPROVE", "Aprobación"
        REJECT = "REJECT", "Rechazo"
        EXPORT = "EXPORT", "Exportación de datos"
        PERMISSION_CHANGE = "PERMISSION_CHANGE", "Cambio de permisos"
        CONFIG_CHANGE = "CONFIG_CHANGE", "Cambio de configuración"
        BACKUP = "BACKUP", "Respaldo"
        OTHER = "OTHER", "Otro"

    class Severity(models.TextChoices):
        INFO = "INFO", "Informativo"
        WARNING = "WARNING", "Advertencia"
        CRITICAL = "CRITICAL", "Crítico"

    class Meta:
        # pyproject.toml permite mover archivos entre apps; sin este app_label
        # Django fijaría el label a partir del módulo y rompería las migraciones.
        app_label = "core"
        verbose_name = "evento de auditoría"
        verbose_name_plural = "auditoría"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["-created_at"], name="idx_audit_created"),
            models.Index(fields=["actor", "-created_at"], name="idx_audit_actor_time"),
            models.Index(fields=["action"], name="idx_audit_action"),
            models.Index(fields=["module", "-created_at"], name="idx_audit_module_time"),
            models.Index(fields=["target_type", "target_id"], name="idx_audit_target"),
        ]

    action = models.CharField("acción", max_length=20, choices=Action.choices)
    severity = models.CharField(
        "gravedad", max_length=10, choices=Severity.choices, default=Severity.INFO
    )
    module = models.CharField("módulo", max_length=40, db_index=True)
    description = models.CharField("descripción", max_length=255, blank=True)

    actor = models.ForeignKey(
        get_user_model(),
        verbose_name="actor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    actor_username = models.CharField("usuario (texto)", max_length=80, blank=True)
    actor_role = models.CharField("rol del actor", max_length=20, blank=True)

    target_type = models.CharField("tipo de objeto", max_length=80, blank=True)
    target_id = models.CharField("ID del objeto", max_length=64, blank=True)
    target_repr = models.CharField("representación", max_length=200, blank=True)
    changes = models.JSONField("cambios", default=dict, blank=True)
    metadata = models.JSONField("metadatos", default=dict, blank=True)

    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("agente de usuario", max_length=300, blank=True)
    request_id = models.CharField("ID de petición", max_length=64, blank=True, db_index=True)
    method = models.CharField("método HTTP", max_length=10, blank=True)
    path = models.CharField("ruta", max_length=255, blank=True)
    status_code = models.PositiveSmallIntegerField("código HTTP", null=True, blank=True)
    duration_ms = models.PositiveIntegerField("duración (ms)", null=True, blank=True)

    created_at = models.DateTimeField("registrado el", default=timezone.now, db_index=True)

    class ImmutableError(RuntimeError):
        """Intento de modificar un evento de auditoría."""

    def __str__(self) -> str:
        actor = self.actor_username or "sistema"
        return f"{self.created_at:%Y-%m-%d %H:%M} · {actor} · {self.action} · {self.module}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise AuditEvent.ImmutableError("Los eventos de auditoría no se pueden modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditEvent.ImmutableError("Los eventos de auditoría no se pueden eliminar.")


# ---------------------------------------------------------------------------
# Contexto de petición (sin depender de middlewares de terceros)
# ---------------------------------------------------------------------------
_audit_context = threading.local()


@contextmanager
def audit_context(**values):
    """Establece el contexto de auditoría durante la petición actual."""
    previous = getattr(_audit_context, "data", {})
    _audit_context.data = {**previous, **values}
    try:
        yield
    finally:
        _audit_context.data = previous


def current_context() -> dict:
    return getattr(_audit_context, "data", {})


def update_context(**values) -> None:
    """Actualiza el contexto vigente (p. ej. tras autenticar al usuario)."""
    previous = getattr(_audit_context, "data", {})
    _audit_context.data = {**previous, **values}


def clear_context(keys=()) -> None:
    """Elimina claves del contexto (p. ej. un ``request`` ya cerrado)."""
    if not keys:
        return
    data = dict(getattr(_audit_context, "data", {}))
    for key in keys:
        data.pop(key, None)
    _audit_context.data = data


def current_user():
    user = current_context().get("user")
    if isinstance(user, SimpleLazyObject):
        try:
            user = user._wrapped  # noqa: SLF001 - acceso intencional a LazyObject
        except Exception:
            return None
    return user if getattr(user, "is_authenticated", False) else None


def client_ip(request) -> str | None:
    from apps.core.utils import client_ip as _client_ip

    return _client_ip(request) or None


# ---------------------------------------------------------------------------
# Registro de eventos
# ---------------------------------------------------------------------------
def _diff(instance, exclude: set[str] | None = None) -> dict:
    """Diferencias entre el estado previo y el actual del objeto."""
    exclude = exclude or set()
    if instance.pk is None or not getattr(instance, "_audit_diff", None):
        return {}
    return instance._audit_diff  # noqa: SLF001


def _serialize(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value][:50]
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in list(value.items())[:50]}
    if isinstance(value, models.Model):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)[:200]


def audit_event(
    *,
    action: str,
    module: str,
    actor=None,
    description: str = "",
    target=None,
    target_type: str = "",
    target_id: str = "",
    target_repr: str = "",
    changes: dict | None = None,
    metadata: dict | None = None,
    severity: str = AuditEvent.Severity.INFO,
    request=None,
    strict: bool = False,
) -> AuditEvent | None:
    """Registra un evento de auditoría.

    :param actor: usuario responsable. Si es ``None`` se toma del contexto.
    :param target: instancia afectada (alternativa a ``target_type``/``target_id``).
    :param strict: si es ``True`` propaga los errores (útil en pruebas).
    """
    try:
        from django.conf import settings

        if not getattr(settings, "AUDIT_ENABLED", True):
            return None

        if target is not None:
            target_type = target_type or type(target).__name__
            target_id = target_id or str(getattr(target, "uuid", None) or target.pk or "")
            target_repr = target_repr or str(target)[:200]

        actor = actor or current_user()
        ctx = current_context()
        request = request or ctx.get("request")

        if actor is not None and not getattr(actor, "is_authenticated", False):
            actor = None

        payload = {
            "action": action,
            "severity": severity,
            "module": module[:40],
            "description": (description or "")[:255],
            "actor": actor,
            "actor_username": getattr(actor, "username", "") if actor else "sistema",
            "actor_role": getattr(actor, "role", "") if actor else "",
            "target_type": (target_type or "")[:80],
            "target_id": str(target_id or "")[:64],
            "target_repr": (target_repr or "")[:200],
            "changes": {k: _serialize(v) for k, v in (changes or {}).items()},
            "metadata": {k: _serialize(v) for k, v in (metadata or {}).items()},
            "request_id": ctx.get("request_id", ""),
        }

        if request is not None:
            from apps.core.utils import client_ip as _client_ip

            payload.update(
                {
                    "ip_address": _client_ip(request) or None,
                    "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:300],
                    "method": (request.method or "")[:10],
                    "path": (request.path or "")[:255],
                }
            )

        return AuditEvent.objects.create(**payload)
    except Exception as exc:  # pragma: no cover - la auditoría no debe romper el negocio
        logger.exception("No se pudo registrar el evento de auditoría: %s", exc)
        if strict:
            raise
        return None


def audit_action(action: str, module: str, description: str = ""):
    """Decorador para auditar acciones de funciones o métodos de vista.

    Uso::

        @audit_action(AuditEvent.Action.EXPORT, "reports", "Exportación de bitácora")
        def export_excel(self, request): ...
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            request = None
            for arg in args:
                if hasattr(arg, "META"):
                    request = arg
                    break
            audit_event(
                action=action,
                module=module,
                description=description or func.__name__,
                request=request,
                metadata={"vista": func.__qualname__},
            )
            return response

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Mixin / señales de auditoría automática
# ---------------------------------------------------------------------------
class AuditedModel(models.Model):
    """Mixin marcador: los cambios del modelo se auditan automáticamente."""

    class Meta:
        abstract = True


def _changes_for(sender, instance) -> dict:
    target = instance
    history = getattr(target, "_audit_history", None)
    if not history:
        return {}
    before, after = history
    changes = {}
    for field_name, new_value in after.items():
        if field_name in SENSITIVE_FIELDS:
            continue
        if before.get(field_name) != new_value:
            changes[field_name] = {
                "antes": _serialize(before.get(field_name)),
                "despues": _serialize(new_value),
            }
    return changes


def _save_history(sender, instance, **kwargs):
    """Captura el estado previo justo antes de guardar."""
    if not isinstance(instance, AuditedModel):
        return
    if instance.pk is None:
        instance._audit_history = ({}, {})  # noqa: SLF001
        return
    try:
        previous = sender._default_manager.get(pk=instance.pk)  # noqa: SLF001
    except sender.DoesNotExist:
        instance._audit_history = ({}, {})  # noqa: SLF001
        return
    before = {f.attname: getattr(previous, f.attname) for f in previous._meta.concrete_fields}
    after = {f.attname: getattr(instance, f.attname) for f in instance._meta.concrete_fields}
    instance._audit_history = (before, after)  # noqa: SLF001


def _on_save(sender, instance, created, raw=False, **kwargs):
    if raw or not isinstance(instance, AuditedModel):
        return
    if sender._meta.app_label not in AUDITED_APPS:  # noqa: SLF001
        return
    changes = _changes_for(sender, instance)
    if not created and not changes:
        return
    audit_event(
        action=AuditEvent.Action.CREATE if created else AuditEvent.Action.UPDATE,
        module=sender._meta.app_label,  # noqa: SLF001
        description=f"{'Creación' if created else 'Modificación'} de {sender._meta.verbose_name}",  # noqa: SLF001
        target=instance,
        changes=changes,
    )


def _on_delete(sender, instance, **kwargs):
    if not isinstance(instance, AuditedModel):
        return
    audit_event(
        action=AuditEvent.Action.DELETE,
        module=sender._meta.app_label,  # noqa: SLF001
        description=f"Eliminación de {sender._meta.verbose_name}",  # noqa: SLF001
        target=instance,
        severity=AuditEvent.Severity.WARNING,
    )


def register_audit_signals():
    """Conecta las señales de todos los modelos auditados.

    Se llama desde ``CoreConfig.ready()`` una sola vez. Usa el registro de
    ContentType para no importar modelos de otras apps prematuramente.
    """
    from django.apps import apps as django_apps

    for model in django_apps.get_models():
        if not issubclass(model, AuditedModel):
            continue
        if model._meta.app_label not in AUDITED_APPS:  # noqa: SLF001
            continue
        uid = f"audit_{model._meta.app_label}_{model._meta.model_name}"  # noqa: SLF001
        # El estado previo debe capturarse ANTES de guardar (pre_save).
        pre_save.connect(
            _save_history,
            sender=model,
            dispatch_uid=f"{uid}_history",
            weak=False,
        )
        post_save.connect(_on_save, sender=model, dispatch_uid=f"{uid}_save", weak=False)
        post_delete.connect(_on_delete, sender=model, dispatch_uid=f"{uid}_delete", weak=False)

    # ``target_type``/``target_id`` guardan la referencia al objeto sin FK, de modo
    # que la auditoría sobrevive al borrado del objeto auditado. ``ContentType``
    # se importa aquí para usarlo desde utilidades que necesiten la etiqueta
    # normalizada ``app_label.model``.
    if not django_apps.is_installed("django.contrib.contenttypes"):  # pragma: no cover
        logger.warning("contenttypes no instalado: se omite la etiqueta normalizada.")
