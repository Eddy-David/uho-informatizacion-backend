"""Utilidades de exportación de documentos (PDF con WeasyPrint, Excel con OpenPyXL).

Se utilizan desde los endpoints de reportes::

    desde apps.core.exports import export_to_excel, export_to_pdf

Ambas funciones devuelven un objeto ``FileResponse``/``HttpResponse`` listo
para enviarse al cliente con las cabeceras de descarga correspondientes.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Iterable, Sequence

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string

try:  # WeasyPrint requiere librerías nativas (pango, cairo)
    from weasyprint import HTML
except Exception:  # pragma: no cover - depende del sistema operativo
    HTML = None


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")


def _safe_title(title: str) -> str:
    return (
        "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in title)
        .strip()
        .replace(" ", "_")
    )


def export_to_excel(
    *,
    title: str,
    headers: Sequence[str],
    rows: Iterable[Sequence],
    sheet_name: str = "Reporte",
    metadata: dict | None = None,
) -> HttpResponse:
    """Genera un libro .xlsx en memoria.

    :param title: Título del documento (también nombre del archivo).
    :param headers: Encabezados de las columnas.
    :param rows: Filas de datos (listas o tuplas).
    :param sheet_name: Nombre de la hoja (máx. 31 caracteres).
    :param metadata: Pares clave/valor que se escriben antes de la tabla.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31] or "Reporte"

    header_fill = PatternFill("solid", fgColor="14305C")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    title_font = Font(bold=True, size=14, color="14305C")
    thin = Side(style="thin", color="D7DEE8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(headers), 1))
    ws.cell(row=1, column=1, value=title).font = title_font
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="center")

    row_cursor = 2
    ws.cell(row=row_cursor, column=1, value=settings.INSTITUTION_NAME).font = Font(
        size=9, italic=True
    )
    row_cursor += 1
    if metadata:
        for key, value in metadata.items():
            ws.cell(row=row_cursor, column=1, value=f"{key}: {value}").font = Font(size=9)
            row_cursor += 1
    row_cursor += 1

    header_row = row_cursor
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    for r, row in enumerate(rows, start=header_row + 1):
        for c, value in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=value)
            cell.border = border
            if isinstance(value, datetime):
                cell.number_format = "yyyy-mm-dd hh:mm"

    for col in range(1, len(headers) + 1):
        max_len = len(str(headers[col - 1]))
        for row in ws.iter_rows(min_row=header_row + 1, min_col=col, max_col=col):
            for cell in row:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[get_column_letter(col)].width = min(max(12, max_len + 2), 45)

    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"{_safe_title(title)}_{_timestamp()}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def export_to_pdf(
    *,
    title: str,
    template_name: str = "reports/table_report.html",
    context: dict | None = None,
    landscape: bool = True,
) -> HttpResponse:
    """Renderiza una plantilla HTML a PDF institucional.

    Si WeasyPrint no está disponible (por ejemplo, falta GTK en Windows),
    devuelve un error 503 explicativo en lugar de fallar silenciosamente.
    """
    if HTML is None:  # pragma: no cover
        return HttpResponse(
            "WeasyPrint no está instalado o faltan sus dependencias nativas. "
            "Consulte docs/INSTALL_WINDOWS.md.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    ctx = {
        "title": title,
        "institution_name": settings.INSTITUTION_NAME,
        "institution_short_name": settings.INSTITUTION_SHORT_NAME,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "generated_at": datetime.now(),
        **(context or {}),
    }
    html = render_to_string(template_name, ctx)
    pdf_bytes = HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf(
        stylesheets=None,
        presentational_hints=True,
    )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"{_safe_title(title)}_{_timestamp()}.pdf"
    disposition = "inline" if ctx.get("inline") else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response
