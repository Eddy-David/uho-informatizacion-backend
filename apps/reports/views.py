"""Vistas de reportes y exportaciones."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control.models import AccessLog
from apps.core.constants import Role
from apps.core.exports import export_to_excel, export_to_pdf
from apps.core.permissions import HasRole
from apps.reports.services import REPORT_TYPES, build_report, dashboard_summary, parse_dates


class IsReportViewer(HasRole):
    allowed_roles = (Role.SUPERADMIN, Role.ADMIN, Role.SECURITY_DIRECTOR)


REPORT_PARAMS = [
    OpenApiParameter("report", str, description=f"Uno de: {', '.join(REPORT_TYPES)}"),
    OpenApiParameter("date_from", str, description="Fecha inicial (YYYY-MM-DD)"),
    OpenApiParameter("date_to", str, description="Fecha final (YYYY-MM-DD)"),
    OpenApiParameter("campus", str, description="Código de sede (opcional)"),
]


class DashboardView(APIView):
    """``GET /api/v1/reports/dashboard/`` — KPIs del panel de inicio."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Indicadores del panel", tags=["Reportes"])
    def get(self, request):
        return Response(dashboard_summary())


class ReportView(APIView):
    """``GET /api/v1/reports/generate/`` — datos tabulares de un reporte."""

    permission_classes = [permissions.IsAuthenticated, IsReportViewer]

    @extend_schema(summary="Generar reporte (JSON)", parameters=REPORT_PARAMS, tags=["Reportes"])
    def get(self, request):
        report_type = request.query_params.get("report", "access-by-day")
        if report_type not in REPORT_TYPES:
            return Response(
                {"detail": f"Reporte inválido. Opciones: {', '.join(REPORT_TYPES)}"}, status=400
            )
        date_from, date_to = parse_dates(request)
        data = build_report(report_type, date_from, date_to, request.query_params.get("campus", ""))
        return Response(
            {
                "report": report_type,
                "label": REPORT_TYPES[report_type],
                "date_from": date_from,
                "date_to": date_to,
                **data,
            }
        )


class ReportExportExcelView(APIView):
    """``GET /api/v1/reports/export/excel/``"""

    permission_classes = [permissions.IsAuthenticated, IsReportViewer]

    @extend_schema(summary="Exportar reporte a Excel", parameters=REPORT_PARAMS, tags=["Reportes"])
    def get(self, request):
        report_type = request.query_params.get("report", "access-by-day")
        if report_type not in REPORT_TYPES:
            return Response({"detail": "Reporte inválido."}, status=400)
        date_from, date_to = parse_dates(request)
        data = build_report(report_type, date_from, date_to, request.query_params.get("campus", ""))
        return export_to_excel(
            title=data["title"],
            headers=data["headers"],
            rows=data["rows"],
            metadata={"Desde": date_from, "Hasta": date_to},
        )


class ReportExportPdfView(APIView):
    """``GET /api/v1/reports/export/pdf/``"""

    permission_classes = [permissions.IsAuthenticated, IsReportViewer]

    @extend_schema(summary="Exportar reporte a PDF", parameters=REPORT_PARAMS, tags=["Reportes"])
    def get(self, request):
        report_type = request.query_params.get("report", "access-by-day")
        if report_type not in REPORT_TYPES:
            return Response({"detail": "Reporte inválido."}, status=400)
        date_from, date_to = parse_dates(request)
        data = build_report(report_type, date_from, date_to, request.query_params.get("campus", ""))
        return export_to_pdf(
            title=data["title"],
            context={
                "headers": data["headers"],
                "rows": data["rows"],
                "filters": {"Desde": date_from, "Hasta": date_to},
            },
        )


class ReportTypesView(APIView):
    """``GET /api/v1/reports/types/`` — catálogo de reportes disponibles."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Tipos de reporte disponibles", tags=["Reportes"])
    def get(self, request):
        return Response([{"value": key, "label": label} for key, label in REPORT_TYPES.items()])


class RecentActivityView(APIView):
    """``GET /api/v1/reports/recent/`` — actividad reciente para el panel."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Actividad reciente", tags=["Reportes"])
    def get(self, request):
        logs = AccessLog.objects.select_related("access_point").order_by("-occurred_at")[:15]
        return Response(
            [
                {
                    "uuid": str(log.uuid),
                    "occurred_at": log.occurred_at,
                    "full_name": log.full_name,
                    "identity_card": log.identity_card,
                    "user_type": log.user_type,
                    "campus": log.campus,
                    "movement": log.movement,
                    "result": log.result,
                    "denial_reason": log.denial_reason,
                }
                for log in logs
            ]
        )
