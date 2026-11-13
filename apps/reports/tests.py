"""Pruebas del endpoint del dashboard (RF-08.5)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import AccessLog

DASHBOARD_URL = "/api/v1/reports/dashboard/"


@pytest.fixture
def operador(django_user_model):
    return django_user_model.objects.create_user(
        username="seg.dashboard", password="x", role="SEG", tipo_usuario="TRABAJADOR"
    )


@pytest.fixture
def cliente(operador):
    client = APIClient()
    client.force_authenticate(user=operador)
    return client


@pytest.mark.django_db
class TestDashboard:
    def test_kpis_en_cero_sin_datos(self, cliente):
        response = cliente.get(DASHBOARD_URL)
        assert response.status_code == 200
        data = response.json()
        assert data["access_today"] == 0
        assert data["active_visitors"] == 0
        assert data["vehicles_inside"] == 0
        assert data["open_incidents"] == 0

    def test_cuenta_solo_registros_de_hoy(self, cliente, django_user_model):
        usuario = django_user_model.objects.create_user(
            username="user.hoy", password="x", tipo_usuario="ESTUDIANTE"
        )
        ahora = timezone.localtime()
        AccessLog.objects.create(
            user=usuario,
            full_name=usuario.nombre_completo,
            identity_card=usuario.ci,
            user_type=usuario.tipo_usuario,
            campus="CENTRAL",
            result=AccessLog.Result.GRANTED,
            movement="ENTRADA",
            occurred_at=ahora,
        )
        # Registro de ayer: no debe contar para "hoy".
        AccessLog.objects.create(
            user=usuario,
            full_name=usuario.nombre_completo,
            identity_card=usuario.ci,
            user_type=usuario.tipo_usuario,
            campus="CENTRAL",
            result=AccessLog.Result.GRANTED,
            movement="ENTRADA",
            occurred_at=ahora - timedelta(days=1),
        )

        data = cliente.get(DASHBOARD_URL).json()
        assert data["access_today"] == 1
        assert data["granted_today"] == 1
        assert data["by_user_type"] == {"ESTUDIANTE": 1}
        assert data["by_hour"] == {str(ahora.hour): 1}

    def test_requiere_autenticacion(self, db):
        assert APIClient().get(DASHBOARD_URL).status_code in (401, 403)

    def test_incluye_series_para_graficas(self, cliente):
        data = cliente.get(DASHBOARD_URL).json()
        assert isinstance(data["by_campus"], dict)
        assert isinstance(data["by_user_type"], dict)
        assert isinstance(data["by_hour"], dict)


GENERATE_URL = "/api/v1/reports/generate/"


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_user(
        username="adm.reportes", password="x", role="SA", tipo_usuario="TRABAJADOR"
    )


@pytest.fixture
def cliente_admin(admin):
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


def _acceso(usuario, campus, movimiento, dias_atras=0):
    """Crea un ``AccessLog`` con fecha relativa a hoy."""
    return AccessLog.objects.create(
        user=usuario,
        full_name=usuario.nombre_completo,
        identity_card=usuario.ci,
        user_type=usuario.tipo_usuario,
        campus=campus,
        result=AccessLog.Result.GRANTED,
        movement=movimiento,
        occurred_at=timezone.localtime() - timedelta(days=dias_atras),
    )


@pytest.mark.django_db
class TestAccessDetailReport:
    """RF-08.6: el listado de accesos de la pantalla es el mismo del PDF/Excel."""

    def test_columnas_del_listado(self, cliente_admin, django_user_model):
        usuario = django_user_model.objects.create_user(
            username="u.detalle", password="x", tipo_usuario="ESTUDIANTE"
        )
        _acceso(usuario, "CENTRAL", "ENTRADA")
        data = cliente_admin.get(GENERATE_URL, {"report": "access-detail"}).json()
        assert data["headers"] == ["Fecha", "Persona", "Sede", "Tipo de movimiento"]
        assert len(data["rows"]) == 1
        fecha, persona, sede, movimiento = data["rows"][0]
        assert persona == usuario.nombre_completo
        assert sede == "CENTRAL"
        assert movimiento == "Entrada"
        assert len(fecha) == 16  # YYYY-MM-DD HH:MM

    def test_filtra_por_sede_y_rango(self, cliente_admin, django_user_model):
        usuario = django_user_model.objects.create_user(
            username="u.filtros", password="x", tipo_usuario="ESTUDIANTE"
        )
        _acceso(usuario, "CENTRAL", "ENTRADA")
        _acceso(usuario, "JULIO_ANTONIO_MELLA", "ENTRADA")
        _acceso(usuario, "CENTRAL", "SALIDA", dias_atras=40)
        hoy = timezone.localdate().isoformat()
        data = cliente_admin.get(
            GENERATE_URL,
            {"report": "access-detail", "campus": "CENTRAL", "date_from": hoy, "date_to": hoy},
        ).json()
        assert len(data["rows"]) == 1
        assert data["rows"][0][2] == "CENTRAL"
        # Los filtros aplicados viajan al PDF y al Excel con el mismo formato.
        assert data["filters"]["Desde"] == hoy
        assert data["filters"]["Hasta"] == hoy

    def test_exportaciones_devuelven_archivos(self, cliente_admin, django_user_model):
        usuario = django_user_model.objects.create_user(
            username="u.export", password="x", tipo_usuario="ESTUDIANTE"
        )
        _acceso(usuario, "CENTRAL", "ENTRADA")
        excel = cliente_admin.get("/api/v1/reports/export/excel/", {"report": "access-detail"})
        assert excel.status_code == 200
        assert excel["Content-Disposition"].startswith("attachment;")
        assert excel.content[:2] == b"PK"  # firma ZIP de .xlsx

        pdf = cliente_admin.get("/api/v1/reports/export/pdf/", {"report": "access-detail"})
        if pdf.status_code == 503:
            pytest.skip("WeasyPrint sin dependencias nativas en este entorno")
        assert pdf.status_code == 200
        assert pdf["Content-Type"] == "application/pdf"
        assert pdf.content[:4] == b"%PDF"

    def test_reporte_invalido_es_400(self, cliente_admin):
        assert cliente_admin.get(GENERATE_URL, {"report": "no-existe"}).status_code == 400


@pytest.mark.django_db
class TestReportesDeListado:
    """RF-08.6: visitas y vehículos también se exportan con la misma tabla."""

    def test_visitas_y_vehiculos_tienen_columnas_y_exportan(self, cliente_admin):
        hoy = timezone.localdate().isoformat()
        for report in ("visits", "vehicles"):
            data = cliente_admin.get(
                GENERATE_URL, {"report": report, "date_from": hoy, "date_to": hoy}
            ).json()
            assert data["report"] == report
            assert data["headers"]

            excel = cliente_admin.get(
                "/api/v1/reports/export/excel/",
                {"report": report, "date_from": hoy, "date_to": hoy},
            )
            assert excel.status_code == 200
            assert excel.content[:2] == b"PK"

    def test_movimientos_vehiculares_formatean_la_fecha(self, cliente_admin):
        from apps.vehicles.models import VehicleMovement

        VehicleMovement.objects.create(
            plate="H123456",
            campus="CENTRAL",
            movement="ENTRADA",
            authorized=True,
            status_after=VehicleMovement.Status.INSIDE,
            occurred_at=timezone.localtime(),
        )
        data = cliente_admin.get(GENERATE_URL, {"report": "vehicles"}).json()
        assert len(data["rows"]) == 1
        fecha, placa, _tipo, movimiento, autorizado, sede = data["rows"][0]
        assert placa == "H123456"
        assert len(fecha) == 16  # YYYY-MM-DD HH:MM, igual que "access-detail"
        assert movimiento == "Entrada"
        assert autorizado == "Sí"
        assert sede == "CENTRAL"
