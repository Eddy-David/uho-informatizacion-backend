"""Composición gráfica del Solapín Digital con Pillow (RF-03.3).

Combina la **plantilla** subida por el administrador (con las ``zones`` en
porcentaje del ancho/alto) con los datos del usuario y el QR del solapín para
obtener la imagen final en PNG.

Zonas reconocidas (RF-03.2):

``photo``         foto del usuario (se recorta ajustada a la zona)
``name``          nombre y apellidos
``identity_card`` carné de identidad
``user_type``     tipo de usuario (Estudiante, Profesor…)
``access_level``  nivel de acceso, con fondo del color secundario
``qr``            código QR (sólo UUID + estado; RF-03.9)
``logo``          reservada para el logo institucional de la plantilla

Cada zona se expresa en porcentaje de la plantilla::

    {"x": 6, "y": 20, "w": 30, "h": 34, "font_size": 4, "align": "left"}
"""

from __future__ import annotations

import logging
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageDraw, ImageFile, ImageFont, ImageOps

from apps.core.utils import render_qr_png

logger = logging.getLogger("apps.solapines")

#: Tamaño del lienzo cuando la plantilla aún no tiene imagen base.
DEFAULT_SIZE = (1011, 638)  # formato tarjeta ISO/IEC 7810 ID-1 a 300 ppp aprox.

#: Colores por defecto si la plantilla no define los suyos.
DEFAULT_PRIMARY = "#14305C"
DEFAULT_SECONDARY = "#D9A441"

#: Fuentes candidatas (se usa la primera disponible en el sistema).
FONT_CANDIDATES = {
    False: (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ),
    True: (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
}

ImageFile.LOAD_TRUNCATED_IMAGES = True


@lru_cache(maxsize=64)
def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Carga la primera fuente TrueType disponible (o la de Pillow)."""
    for path in FONT_CANDIDATES[bold]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    logger.warning("No se encontró fuente TrueType; se usa la fuente por defecto de Pillow.")
    return ImageFont.load_default()


def _rgb(value: str | None, fallback: str) -> tuple[int, int, int]:
    """Convierte ``#RRGGBB`` + alpha opcional en una tupla RGB válida."""
    hex_color = (value or fallback).strip().lstrip("#")
    if len(hex_color) == 8:
        hex_color = hex_color[:6]
    try:
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    except (ValueError, TypeError):
        return _rgb(fallback, DEFAULT_PRIMARY)


def _is_light(color: tuple[int, int, int]) -> bool:
    """Luminancia relativa: decide si el texto de la zona debe ser negro o blanco."""
    r, g, b = color
    return (0.299 * r + 0.587 * g + 0.114 * b) > 150


def _box(zone: dict, width: int, height: int) -> tuple[int, int, int, int]:
    """Traduce una zona porcentual a un rectángulo ``(x1, y1, x2, y2)`` en píxeles."""
    x1 = int(width * float(zone.get("x", 0)) / 100)
    y1 = int(height * float(zone.get("y", 0)) / 100)
    x2 = x1 + int(width * float(zone.get("w", 0)) / 100)
    y2 = y1 + int(height * float(zone.get("h", 0)) / 100)
    # Ninguna zona puede salirse del lienzo de la plantilla.
    x1, y1 = min(max(0, x1), width), min(max(0, y1), height)
    x2, y2 = min(max(x1, x2), width), min(max(y1, y2), height)
    return x1, y1, x2, y2


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Divide el texto en líneas que caben dentro del ancho de la zona."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _zones_from_palette(primary: str, secondary: str) -> dict:
    """Zonas por defecto cuando la plantilla no define ``zones``."""
    return {
        "photo": {"x": 6, "y": 20, "w": 30, "h": 40},
        "name": {"x": 40, "y": 22, "w": 54, "h": 12},
        "identity_card": {"x": 40, "y": 36, "w": 54, "h": 8},
        "user_type": {"x": 40, "y": 46, "w": 54, "h": 6},
        "qr": {"x": 64, "y": 58, "w": 28, "h": 34},
        "access_level": {"x": 6, "y": 76, "w": 50, "h": 11},
    }


def _draw_placeholder(canvas: Image.Image, primary: str, secondary: str) -> None:
    """Pinta una plantilla por defecto si el administrador no subió imagen base."""
    draw = ImageDraw.Draw(canvas)
    width, height = canvas.size
    draw.rectangle((0, 0, width, height), fill=_rgb(primary, DEFAULT_PRIMARY))
    # Franja superior con el nombre de la institución.
    draw.rectangle((0, 0, width, int(height * 0.16)), fill=_rgb(secondary, DEFAULT_SECONDARY))
    font = _load_font(max(16, int(height * 0.07)), bold=True)
    draw.text(
        (int(width * 0.05), int(height * 0.04)),
        "UNIVERSIDAD DE HOLGUÍN",
        font=font,
        fill=_rgb(primary, DEFAULT_PRIMARY),
    )
    # Franja inferior de contraste.
    draw.rectangle((0, int(height * 0.9), width, height), fill=_rgb(secondary, DEFAULT_SECONDARY))


def _paste_photo(canvas: Image.Image, box: tuple[int, int, int, int], user, primary: str) -> None:
    """Estampa la foto del usuario recortada a la zona (o sus iniciales)."""
    x1, y1, x2, y2 = box
    if x2 - x1 < 2 or y2 - y1 < 2:
        return
    image = None
    foto = getattr(user, "foto", None)
    if foto:
        try:
            foto.open("rb")
            image = Image.open(foto).convert("RGB")
        except (OSError, ValueError) as exc:  # archivo ausente o corrupto
            logger.warning("No se pudo abrir la foto de %s: %s", user, exc)
        finally:
            try:
                foto.close()
            except Exception:  # noqa: BLE001 - el storage puede ya estar cerrado
                pass

    if image is None:
        # Sin foto: iniciales sobre el color primario.
        placeholder = Image.new("RGB", (x2 - x1, y2 - y1), _rgb(primary, DEFAULT_PRIMARY))
        draw = ImageDraw.Draw(placeholder)
        initials = getattr(user, "initials", "") or ""
        if initials:
            font = _load_font(max(10, int((y2 - y1) * 0.4)), bold=True)
            draw.text(
                ((x2 - x1) / 2, (y2 - y1) / 2),
                initials,
                font=font,
                fill=(255, 255, 255),
                anchor="mm",
            )
            canvas.paste(placeholder, (x1, y1))
        return

    thumbnail = ImageOps.fit(image, (x2 - x1, y2 - y1), centering=(0.5, 0.35))
    canvas.paste(thumbnail, (x1, y1))


def _paste_qr(canvas: Image.Image, box: tuple[int, int, int, int], payload: str) -> None:
    """Genera el QR y lo centra en su zona sobre fondo blanco."""
    x1, y1, x2, y2 = box
    side = min(x2 - x1, y2 - y1)
    if side < 16:
        return
    qr_image = Image.open(BytesIO(render_qr_png(payload, box_size=10, border=2)))
    qr_image = qr_image.convert("RGB").resize((side, side), Image.NEAREST)
    canvas.paste(qr_image, (x1 + (x2 - x1 - side) // 2, y1 + (y2 - y1 - side) // 2))


def _draw_text(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    color: tuple[int, int, int],
    bold: bool = True,
    background: tuple[int, ...] | None = None,
    font_size: float | None = None,
) -> None:
    """Escribe ``text`` dentro de la zona, ajustando tamaño y líneas."""
    x1, y1, x2, y2 = box
    box_w, box_h = x2 - x1, y2 - y1
    if not text or box_w < 4 or box_h < 4:
        return
    if background is not None:
        radius = max(2, box_h // 5)
        if len(background) == 4:
            # Viñeta con transparencia: se dibuja enmascarada para difuminar el borde.
            _pill(canvas, box, radius, background)
        else:
            draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=background)
        # Margen interno para que el texto no toque el borde de la píldora.
        pad = max(2, int(box_h * 0.18))
        x1, y1, x2, y2 = x1 + pad, y1 + pad, x2 - pad, y2 - pad
        box_w, box_h = x2 - x1, y2 - y1

    base_size = int(box_h * (font_size if font_size else 0.72))
    font = _load_font(max(8, base_size), bold=bold)
    lines = _wrap_text(draw, text, font, box_w)
    line_height = int(font.size * 1.15)
    # Si las líneas no caben, se reduce la fuente progresivamente.
    while len(lines) * line_height > box_h and font.size > 8:
        font = _load_font(font.size - 1, bold=bold)
        lines = _wrap_text(draw, text, font, box_w)
        line_height = int(font.size * 1.15)

    total = len(lines) * line_height
    y = y1 + max(0, (box_h - total) // 2)
    for line in lines:
        draw.text((x1, y), line, font=font, fill=color + (255,) if len(color) == 3 else color)
        y += line_height


def _pill(canvas: Image.Image, box: tuple[int, int, int, int], radius: int, color) -> None:
    """Dibuja una viñeta redondeada semitransparente con el borde suavizado."""
    x1, y1, x2, y2 = box
    width, height = max(1, x2 - x1), max(1, y2 - y1)
    if width < 2 or height < 2:
        return
    # Máscara 4x para que el redondeo no salga con dientes de sierra.
    scale = 4
    mask = Image.new("L", (width * scale, height * scale), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, width * scale - 1, height * scale - 1), radius=radius * scale, fill=color[3]
    )
    mask = mask.resize((width, height), Image.LANCZOS)
    fill = Image.new("RGBA", (width, height), color[:3] + (255,))
    canvas.paste(fill, (x1, y1), mask)


def compose_badge_image(badge) -> bytes:
    """Compone el Solapín Digital de ``badge`` y devuelve el PNG en bytes (RF-03.3).

    :param badge: instancia de :class:`~apps.solapines.models.Badge` con
        ``user`` y ``template`` precargados (``select_related``).
    """
    template = badge.template
    user = badge.user
    primary = getattr(template, "primary_color", None) or DEFAULT_PRIMARY
    secondary = getattr(template, "secondary_color", None) or DEFAULT_SECONDARY

    # 1) Lienzo: imagen base de la plantilla o tarjeta por defecto.
    canvas = None
    if template is not None and template.background_image:
        try:
            template.background_image.open("rb")
            canvas = Image.open(template.background_image).convert("RGBA")
        except (OSError, ValueError) as exc:
            logger.warning("Plantilla %s sin imagen base legible: %s", template, exc)
        finally:
            try:
                template.background_image.close()
            except Exception:  # noqa: BLE001
                pass

    if canvas is None:
        canvas = Image.new("RGBA", DEFAULT_SIZE, _rgb(primary, DEFAULT_PRIMARY) + (255,))
        _draw_placeholder(canvas, primary, secondary)

    zones = (getattr(template, "zones", None) or {}).copy()
    defaults = _zones_from_palette(primary, secondary)
    for key, value in defaults.items():
        zones.setdefault(key, value)

    # 2) Foto y QR son imágenes: se estampan sobre el lienzo.
    if zones.get("photo"):
        _paste_photo(canvas, _box(zones["photo"], *canvas.size), user, primary)
    if zones.get("qr"):
        _paste_qr(canvas, _box(zones["qr"], *canvas.size), badge.qr_payload)

    # 3) Textos con viñetas de contraste: RGBA permite difuminar las "píldoras"
    #    sin alterar la plantilla original. La opacidad se calcula con el color
    #    real del fondo: sobre fondos oscuros una viñeta translúcida no se notaría.
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    def draw_field(zone_name: str, text: str, *, bold: bool = False) -> None:
        """Pinta un dato con el color y la viñeta que contrasten con su zona."""
        if not zones.get(zone_name) or not text:
            return
        box = _box(zones[zone_name], *canvas.size)
        brightness = _mean_brightness(canvas, box)
        color = _text_on(brightness, primary)
        _draw_text(
            layer,
            draw,
            box,
            text,
            color=color,
            bold=bold,
            background=_contrast_pill(color, brightness),
        )

    draw_field("name", user.nombre_completo, bold=True)
    draw_field("identity_card", f"CI: {user.ci}" if user.ci else "")
    draw_field("user_type", user.get_tipo_usuario_display())

    secondary_rgb = _rgb(secondary, DEFAULT_SECONDARY)
    if zones.get("access_level"):
        _draw_text(
            layer,
            draw,
            _box(zones["access_level"], *canvas.size),
            f"NIVEL: {badge.get_access_level_display().upper()}",
            color=(17, 24, 39) if _is_light(secondary_rgb) else (255, 255, 255),
            bold=True,
            background=secondary_rgb + (255,),
        )

    # 4) Se combina la capa de texto con el lienzo (el QR queda nítido encima).
    canvas = Image.alpha_composite(canvas.convert("RGBA"), layer)

    buffer = BytesIO()
    canvas.convert("RGB").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _mean_brightness(canvas: Image.Image, box: tuple[int, int, int, int]) -> float:
    """Brillo medio (0-255) de la plantilla bajo la zona indicada.

    Se muestrea la zona en una rejilla reducida: barato incluso con plantillas
    de alta resolución y suficiente para elegir el color del texto.
    """
    x1, y1, x2, y2 = box
    if x2 <= x1 or y2 <= y1:
        return 255.0
    sample = canvas.convert("RGB").crop((x1, y1, x2, y2)).resize((16, 16))
    pixels = list(sample.getdata())
    luminances = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels]
    return sum(luminances) / len(luminances)


def _text_on(brightness: float, primary: str) -> tuple[int, int, int]:
    """Color de texto legible según el brillo medio del fondo de la zona.

    Fondo oscuro → texto blanco. Fondo claro → se reutiliza el color primario si
    contrasta lo suficiente; si no (plantilla a color), se usa un gris muy oscuro.
    """
    if brightness <= 150:
        return (255, 255, 255)
    primario = _rgb(primary, DEFAULT_PRIMARY)
    return primario if not _is_light(primario) else (17, 24, 39)


def _contrast_pill(color: tuple[int, int, int], background: float) -> tuple[int, int, int, int]:
    """Viñeta opuesta al color del texto, con opacidad según el fondo de la zona.

    El texto claro va sobre una viñeta oscura y viceversa. La opacidad crece
    cuanto menos contrasta el fondo de la plantilla con la viñeta: sobre fondos
    oscuros la viñeta oscura se vuelve casi opaca para que el bloque se lea.
    """
    if _is_light(color):
        # Texto claro → viñeta oscura; el fondo oscuro exige mayor opacidad.
        alpha = 90 + int((255 - background) * 0.6)
        return (13, 20, 38, min(245, alpha))
    # Texto oscuro → viñeta clara; el fondo claro exige mayor opacidad.
    alpha = 90 + int(background * 0.6)
    return (255, 255, 255, min(245, alpha))
