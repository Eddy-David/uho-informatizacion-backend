"""Lógica de reportes: agregaciones y construcción de conjuntos de datos.

Se separa de las vistas para poder reutilizarse desde tareas programadas o
desde la línea de comandos (management command ``generate_report``).
"""

from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Count, Q
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone

from apps.access_control.models import AccessLog
from apps.incidents.models import Incident
from apps.vehicles.models import VehicleMovement
from apps.visitors.models import VisitRequest

REPORT_TYPES = {
    "access-by-day": "Accesos por día",
    "access-by-hour": "Accesos por hora",
    "access-by-campus": "Accesos por sede",
    "access-denied": "Accesos denegados",
    "users-by-type": "Usuarios por tipo",
    "visits": "Solicitudes de visita",
    "vehicles": "Movimientos vehiculares",
    "incidents": "Incidencias",
}


def parse_dates(request) -> tuple[date, date]:
    """Obtiene ``date_from``/``date_to`` de los query params (por defecto 30 días)."""
    today = timezone.localdate()
    try:
        date_from = date.fromisoformat(request.query_params.get("date_from", ""))
    except ValueError:
        date_from = today - timedelta(days=30)
    try:
        date_to = date.fromisoformat(request.query_params.get("date_to", ""))
    except ValueError:
        date_to = today
    return date_from, date_to


def dashboard_summary() -> dict:
    """Indicadores del panel de inicio."""
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    access_today = AccessLog.objects.filter(occurred_at__date=today)
    access_yesterday = AccessLog.objects.filter(occurred_at__date=yesterday)

    from apps.usuarios.models import User

    total_today = access_today.count()
    total_yesterday = access_yesterday.count()
    variation = (
        round(((total_today - total_yesterday) / total_yesterday) * 100, 1)
        if total_yesterday
        else None
    )

    return {
        "date": today,
        "access_today": total_today,
        "access_yesterday": total_yesterday,
        "access_variation_pct": variation,
        "granted_today": access_today.filter(result=AccessLog.Result.GRANTED).count(),
        "denied_today": access_today.filter(result=AccessLog.Result.DENIED).count(),
        "inside_now": access_today.filter(
            result=AccessLog.Result.GRANTED, movement="ENTRADA"
        ).count(),
        "active_users": User.objects.filter(estado=True).count(),
        "active_visitors": VisitRequest.objects.filter(
            status=VisitRequest.Status.APPROVED, valid_from__lte=today, valid_until__gte=today
        ).count(),
        "vehicles_inside": VehicleMovement.objects.filter(
            occurred_at__date=today, status_after=VehicleMovement.Status.INSIDE
        )
        .values("plate")
        .distinct()
        .count(),
        "open_incidents": Incident.objects.exclude(
            status__in=(Incident.Status.CLOSED, Incident.Status.DISMISSED)
        ).count(),
        "pending_visits": VisitRequest.objects.filter(status=VisitRequest.Status.PENDING).count(),
        "by_campus": {
            item["campus"] or "SIN_SEDE": item["total"]
            for item in access_today.values("campus").annotate(total=Count("id"))
        },
        "by_hour": {
            str(item["hour"]): item["total"]
            for item in access_today.annotate(hour=ExtractHour("occurred_at"))
            .values("hour")
            .annotate(total=Count("id"))
            .order_by("hour")
        },
    }


def build_report(report_type: str, date_from: date, date_to: date, campus: str = "") -> dict:
    """Devuelve ``{"headers": [...], "rows": [[...]], "title": str}``."""
    access_qs = AccessLog.objects.filter(occurred_at__date__range=(date_from, date_to))
    if campus:
        access_qs = access_qs.filter(campus=campus)

    if report_type == "access-by-day":
        data = (
            access_qs.annotate(day=TruncDate("occurred_at"))
            .values("day")
            .annotate(
                total=Count("id"),
                granted=Count("id", filter=Q(result=AccessLog.Result.GRANTED)),
                denied=Count("id", filter=Q(result=AccessLog.Result.DENIED)),
            )
            .order_by("day")
        )
        return {
            "title": "Accesos por día",
            "headers": ["Fecha", "Total", "Permitidos", "Denegados"],
            "rows": [[r["day"], r["total"], r["granted"], r["denied"]] for r in data],
        }

    if report_type == "access-by-hour":
        data = (
            access_qs.annotate(hour=ExtractHour("occurred_at"))
            .values("hour")
            .annotate(total=Count("id"))
            .order_by("hour")
        )
        return {
            "title": "Accesos por hora",
            "headers": ["Hora", "Total"],
            "rows": [[f"{r['hour']:02d}:00", r["total"]] for r in data],
        }

    if report_type == "access-by-campus":
        data = access_qs.values("campus").annotate(total=Count("id")).order_by("-total")
        return {
            "title": "Accesos por sede",
            "headers": ["Sede", "Total"],
            "rows": [[r["campus"] or "Sin sede", r["total"]] for r in data],
        }

    if report_type == "access-denied":
        data = access_qs.filter(result=AccessLog.Result.DENIED).order_by("-occurred_at")[:5000]
        return {
            "title": "Accesos denegados",
            "headers": ["Fecha", "Nombre", "CI", "Sede", "Motivo"],
            "rows": [
                [
                    timezone.localtime(r.occurred_at).replace(tzinfo=None),
                    r.full_name,
                    r.identity_card,
                    r.campus,
                    r.denial_reason,
                ]
                for r in data
            ],
        }

    if report_type == "users-by-type":
        from apps.usuarios.models import User

        data = User.objects.filter(estado=True).values("tipo_usuario").annotate(total=Count("id"))
        return {
            "title": "Usuarios activos por tipo",
            "headers": ["Tipo de usuario", "Total"],
            "rows": [[r["tipo_usuario"], r["total"]] for r in data],
        }

    if report_type == "visits":
        data = VisitRequest.objects.filter(created_at__date__range=(date_from, date_to)).order_by(
            "-created_at"
        )
        return {
            "title": "Solicitudes de visita",
            "headers": ["Código", "Visitante", "CI", "Sede", "Área", "Desde", "Hasta", "Estado"],
            "rows": [
                [
                    r.code,
                    r.visitor_name,
                    r.visitor_identity_card,
                    r.campus,
                    r.area,
                    r.valid_from,
                    r.valid_until,
                    r.get_status_display(),
                ]
                for r in data
            ],
        }

    if report_type == "vehicles":
        data = VehicleMovement.objects.filter(
            occurred_at__date__range=(date_from, date_to)
        ).order_by("-occurred_at")
        if campus:
            data = data.filter(campus=campus)
        return {
            "title": "Movimientos vehiculares",
            "headers": ["Fecha", "Placa", "Tipo", "Movimiento", "Autorizado", "Sede"],
            "rows": [
                [
                    timezone.localtime(r.occurred_at).replace(tzinfo=None),
                    r.plate,
                    r.vehicle_type,
                    r.get_movement_display(),
                    "Sí" if r.authorized else "No",
                    r.campus,
                ]
                for r in data
            ],
        }

    if report_type == "incidents":
        data = Incident.objects.filter(occurred_at__date__range=(date_from, date_to))
        if campus:
            data = data.filter(campus=campus)
        data = data.order_by("-occurred_at")
        return {
            "title": "Incidencias",
            "headers": ["Código", "Fecha", "Título", "Tipo", "Gravedad", "Estado", "Sede"],
            "rows": [
                [
                    r.code,
                    timezone.localtime(r.occurred_at).replace(tzinfo=None),
                    r.title,
                    r.incident_type,
                    r.get_severity_display(),
                    r.get_status_display(),
                    r.campus,
                ]
                for r in data
            ],
        }

    raise ValueError(f"Tipo de reporte no soportado: {report_type}")
