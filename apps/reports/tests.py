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
