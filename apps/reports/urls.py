"""Rutas de reportes."""

from django.urls import path

from apps.reports.views import (
    DashboardView,
    RecentActivityView,
    ReportExportExcelView,
    ReportExportPdfView,
    ReportTypesView,
    ReportView,
)

app_name = "reports"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("recent/", RecentActivityView.as_view(), name="recent"),
    path("types/", ReportTypesView.as_view(), name="types"),
    path("generate/", ReportView.as_view(), name="generate"),
    path("export/excel/", ReportExportExcelView.as_view(), name="export-excel"),
    path("export/pdf/", ReportExportPdfView.as_view(), name="export-pdf"),
]
