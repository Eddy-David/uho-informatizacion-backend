"""Endpoint de salud del sistema (usado por Docker healthchecks y monitoreo)."""

from __future__ import annotations

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """``GET /api/v1/health/`` — estado de la API y de la base de datos."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request):
        database_ok = True
        database_error = None
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:  # pragma: no cover - solo en fallos de infraestructura
            database_ok = False
            database_error = str(exc)

        status_code = 200 if database_ok else 503
        return Response(
            {
                "status": "ok" if database_ok else "degraded",
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.DJANGO_ENV,
                "database": {"ok": database_ok, "error": database_error},
                "server_time": timezone.now().isoformat(),
            },
            status=status_code,
        )


class AboutView(APIView):
    """``GET /api/v1/about/`` — identidad institucional y configuración visible."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request):
        return Response(
            {
                "app_name": settings.APP_NAME,
                "app_version": settings.APP_VERSION,
                "institution": settings.INSTITUTION_NAME,
                "institution_short_name": settings.INSTITUTION_SHORT_NAME,
                "timezone": settings.TIME_ZONE,
                "environment": settings.DJANGO_ENV,
                "integrations": {
                    name: {"enabled": cfg["enabled"]}
                    for name, cfg in settings.UHO_INTEGRATIONS.items()
                },
            }
        )
