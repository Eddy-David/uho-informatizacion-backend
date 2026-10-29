"""Lógica de verificación de acceso.

La verificación es deliberadamente centralizada en este servicio para que
tanto la web como la PWA y la app móvil compartan las mismas reglas:

1. Resolver la persona (QR, número de solapín o CI).
2. Comprobar existencia y vigencia del solapín.
3. Comprobar el estado de la cuenta del usuario.
4. Comprobar restricciones por sede / punto de control (futuro).
5. Registrar el movimiento en la bitácora.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from django.utils import timezone

from apps.access_control.models import AccessLog
from apps.usuarios.models import User
from apps.core.constants import AccessLevel, MovementType
from apps.core.utils import client_ip, extract_codigo_qr, normalize_identity_card
from apps.solapines.models import Badge


class DenialReason:
    """Códigos estables de denegación (usados también por el frontend)."""

    NOT_FOUND = "NO_ENCONTRADO"
    BADGE_CANCELLED = "SOLAPIN_CANCELADO"
    BADGE_SUSPENDED = "SOLAPIN_SUSPENDIDO"
    BADGE_EXPIRED = "SOLAPIN_VENCIDO"
    BADGE_NOT_STARTED = "SOLAPIN_NO_VIGENTE"
    USER_INACTIVE = "USUARIO_INACTIVO"
    ALREADY_INSIDE = "YA_DENTRO"
    NOT_INSIDE = "NO_ESTA_DENTRO"
    INVALID_LEVEL = "NIVEL_NO_PERMITIDO"

    LABELS = {
        NOT_FOUND: "Persona o solapín no encontrado.",
        BADGE_CANCELLED: "El solapín fue cancelado.",
        BADGE_SUSPENDED: "El solapín está suspendido.",
        BADGE_EXPIRED: "El solapín está vencido.",
        BADGE_NOT_STARTED: "El solapín aún no es vigente.",
        USER_INACTIVE: "La cuenta del usuario está deshabilitada.",
        ALREADY_INSIDE: "La persona ya tiene una entrada activa sin salida.",
        NOT_INSIDE: "La persona no registra entrada previa.",
        INVALID_LEVEL: "El nivel de acceso no permite este movimiento.",
    }


@dataclass
class VerificationResult:
    allowed: bool
    reason: str = ""
    message: str = ""
    user: Optional[User] = None
    badge: Optional[Badge] = None
    log: Optional[AccessLog] = None
    warnings: list[str] = field(default_factory=list)


#: Alias privado por compatibilidad con pruebas y llamadas internas.
_extract_codigo_qr = extract_codigo_qr


def _resolve(qr_token: str = "", badge_number: str = "", identity_card: str = ""):
    """Devuelve (user, badge) según el criterio recibido."""
    if qr_token:
        badge = Badge.objects.select_related("user").filter(qr_token=qr_token).first()
        if badge is None:
            # El QR del solapín contiene el UUID público (RF-03.9).
            codigo = _extract_codigo_qr(qr_token)
            if codigo:
                try:
                    uuid.UUID(str(codigo))
                except (ValueError, AttributeError, TypeError):
                    # No es un UUID (p. ej. un CI): seguir con los otros criterios.
                    badge = None
                else:
                    badge = Badge.objects.select_related("user").filter(codigo_qr=codigo).first()
        return (badge.user, badge) if badge else (None, None)

    if badge_number:
        badge = (
            Badge.objects.select_related("user").filter(badge_number__iexact=badge_number).first()
        )
        return (badge.user, badge) if badge else (None, None)

    ci = normalize_identity_card(identity_card)
    if not ci:
        return None, None

    user = User.objects.filter(ci=ci).first()
    if user is None:
        return None, None
    badge = Badge.objects.filter(user=user).order_by("-issued_at").first()
    return user, badge


def verify_access(
    *,
    operator: User,
    movement: str = MovementType.ENTRY,
    qr_token: str = "",
    badge_number: str = "",
    identity_card: str = "",
    campus: str = "",
    access_point=None,
    channel: str = AccessLog.Channel.WEB,
    request=None,
    client_uuid=None,
    device_info: str = "",
    observed: str = "",
    occurred_at=None,
) -> VerificationResult:
    """Verifica el acceso y, si procede, registra el movimiento.

    :param occurred_at: hora real del movimiento cuando se lee de la cola
        offline (RNF-09). Sin valor se usa la hora del servidor; si el reloj
        del dispositivo está adelantado se recorta a ``ahora``.
    """
    user, badge = _resolve(
        qr_token=qr_token, badge_number=badge_number, identity_card=identity_card
    )

    if user is None:
        return VerificationResult(
            allowed=False,
            reason=DenialReason.NOT_FOUND,
            message=DenialReason.LABELS[DenialReason.NOT_FOUND],
        )

    now = timezone.localtime()

    denial = None
    if not user.is_active:
        denial = DenialReason.USER_INACTIVE
    elif badge is None:
        denial = DenialReason.NOT_FOUND
    elif badge.status == Badge.Status.CANCELLED:
        denial = DenialReason.BADGE_CANCELLED
    elif badge.status == Badge.Status.SUSPENDED:
        denial = DenialReason.BADGE_SUSPENDED
    elif badge.status == Badge.Status.EXPIRED:
        # El estado del solapín manda aunque no tenga fecha de vencimiento.
        denial = DenialReason.BADGE_EXPIRED
    elif badge.expires_at and badge.expires_at < now:
        denial = DenialReason.BADGE_EXPIRED
    elif badge.valid_from and badge.valid_from > now.date():
        denial = DenialReason.BADGE_NOT_STARTED
    elif badge.valid_until and badge.valid_until < now.date():
        denial = DenialReason.BADGE_EXPIRED
    elif badge.access_level == AccessLevel.VISITOR and badge.expires_at and badge.expires_at < now:
        # Regla 3: el solapín de visitante sólo vale dentro de su vigencia.
        denial = DenialReason.BADGE_EXPIRED

    logged_at = now
    if occurred_at is not None:
        logged_at = timezone.localtime(occurred_at)
        if logged_at > now:
            logged_at = now

    log = AccessLog.objects.create(
        user=user,
        badge=badge,
        full_name=user.nombre_completo,
        identity_card=user.ci,
        user_type=user.tipo_usuario,
        access_level=badge.access_level if badge else user.nivel_acceso,
        campus=campus or user.campus,
        access_point=access_point,
        movement=movement,
        result=AccessLog.Result.DENIED if denial else AccessLog.Result.GRANTED,
        denial_reason=denial or "",
        channel=channel,
        registered_by=operator,
        occurred_at=logged_at,
        client_uuid=client_uuid,
        source_ip=client_ip(request) if request is not None else None,
        device_info=device_info[:200],
        observed=observed[:255],
        synced_at=now if channel == AccessLog.Channel.PWA else None,
    )

    if denial:
        return VerificationResult(
            allowed=False,
            reason=denial,
            message=DenialReason.LABELS[denial],
            user=user,
            badge=badge,
            log=log,
        )

    return VerificationResult(
        allowed=True, message="Acceso permitido.", user=user, badge=badge, log=log
    )


def datos_persona(user, badge) -> dict:
    """Datos mínimos de la ficha de verificación (RF-04.3)."""
    foto = ""
    if user is not None and getattr(user, "foto", None):
        try:
            foto = user.foto.url
        except (ValueError, AttributeError):
            foto = ""
    return {
        "nombre": user.nombre_completo if user else "",
        "tipo": user.get_tipo_usuario_display() if user else "",
        "nivel": badge.get_access_level_display() if badge else "",
        "foto": foto,
    }


def verificar_acceso(codigo_o_ci: str, *, movement: str = MovementType.ENTRY) -> VerificationResult:
    """Motor de verificación (RF-04). **No registra** el movimiento.

    ``codigo_o_ci`` admite el UUID del QR, el payload JSON del QR, el número de
    solapín o el carné de identidad. Aplica estrictamente las reglas:

    1. Sin solapín/persona            → denegar (NO_ENCONTRADO).
    2. Cuenta deshabilitada           → denegar (USUARIO_INACTIVO).
    3. Estado CANCELADO               → denegar **siempre** (regla 2).
    4. Estado VENCIDO / expiración    → denegar (regla 3 para visitantes).
    5. Resto                          → permitir.
    """
    texto = (codigo_o_ci or "").strip()
    user, badge = _resolve(qr_token=texto, badge_number=texto)

    if user is None:
        user = (
            User.objects.filter(ci=normalize_identity_card(texto)).first()
            if normalize_identity_card(texto)
            else None
        )
        if user is not None:
            badge = (
                Badge.objects.select_related("user")
                .filter(user=user)
                .order_by("-issued_at")
                .first()
            )

    if user is None:
        return VerificationResult(
            allowed=False,
            reason=DenialReason.NOT_FOUND,
            message=DenialReason.LABELS[DenialReason.NOT_FOUND],
        )

    now = timezone.localtime()
    denial = None
    if not user.is_active:
        denial = DenialReason.USER_INACTIVE
    elif badge is None:
        denial = DenialReason.NOT_FOUND
    elif badge.status == Badge.Status.CANCELLED:
        denial = DenialReason.BADGE_CANCELLED
    elif badge.status == Badge.Status.SUSPENDED:
        denial = DenialReason.BADGE_SUSPENDED
    elif badge.status == Badge.Status.EXPIRED:
        denial = DenialReason.BADGE_EXPIRED
    elif badge.expires_at and badge.expires_at < now:
        denial = DenialReason.BADGE_EXPIRED
    elif badge.access_level == AccessLevel.VISITOR and badge.valid_until:
        if badge.valid_until < now.date():
            denial = DenialReason.BADGE_EXPIRED
    elif badge.valid_from and badge.valid_from > now.date():
        denial = DenialReason.BADGE_NOT_STARTED

    return VerificationResult(
        allowed=denial is None,
        reason=denial or "",
        message=DenialReason.LABELS[denial] if denial else "Acceso permitido.",
        user=user,
        badge=badge,
    )
