"""Utilidades de negocio transversales."""

from __future__ import annotations

import json
import secrets
import string

from django.utils import timezone

ALPHABET = string.ascii_uppercase + string.digits


def generate_public_code(prefix: str = "", length: int = 10) -> str:
    """Genera un código público legible (sin caracteres ambiguos)."""
    alphabet = ALPHABET.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    body = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{body}" if prefix else body


def normalize_identity_card(value: str) -> str:
    """Normaliza un número de Carnet de Identidad a 11 dígitos."""
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return digits.zfill(11) if digits else ""


def generate_qr_token() -> str:
    """Token aleatorio embebido en el QR del Solapín Digital."""
    return secrets.token_urlsafe(24)


def qr_payload(codigo_qr, estado: str) -> str:
    """Contenido del QR de un Solapín (RF-03.9).

    Sólo incluye el UUID público y el estado: **nunca** datos personales
    (nombre, CI, foto, área ni nivel de acceso).
    """
    return json.dumps({"uuid": str(codigo_qr), "estado": str(estado)}, separators=(",", ":"))


def render_qr_png(payload: str, box_size: int = 10, border: int = 2) -> bytes:
    """Renderiza el contenido del QR a PNG (bytes) con la librería ``qrcode``."""
    import qrcode
    from io import BytesIO

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def today_range():
    """Devuelve el rango [inicio, fin] del día actual en la zona horaria local."""
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timezone.timedelta(days=1)
    return start, end


def client_ip(request) -> str:
    """Obtiene la IP real del cliente respetando proxies inversos (nginx)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
