"""Pruebas del flujo completo de visitas (RF-05)."""

from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.solapines.models import Badge
from apps.visitors.models import VisitRequest

REQUESTS_URL = "/api/v1/visitors/requests/"


def _solicitud_payload():
    hoy = timezone.localdate()
    return {
        "visitor_name": "Carlos Pérez Demo",
        "visitor_identity_card": "92031245678",
        "visitor_phone": "53123456",
        "visitor_organization": "UHo Demo",
        "reason": "Reunión de coordinación académica",
        "area": "Facultad de Informática",
        "campus": "CENTRAL",
        "valid_from": str(hoy),
        "valid_until": str(hoy + timezone.timedelta(days=2)),
    }


@pytest.fixture
def cuadro(django_user_model):
    return django_user_model.objects.create_user(
        username="cuadro.rf05", password="x", role="CUADRO", tipo_usuario="CUADRO"
    )


@pytest.fixture
def aprobador(django_user_model):
    return django_user_model.objects.create_user(
        username="aprobador.rf05", password="x", role="AV", tipo_usuario="TRABAJADOR"
    )


@pytest.fixture
def cliente_cuadro(cuadro):
    client = APIClient()
    client.force_authenticate(user=cuadro)
    return client


@pytest.fixture
def cliente_aprobador(aprobador):
    client = APIClient()
    client.force_authenticate(user=aprobador)
    return client


@pytest.fixture
def solicitud(cliente_cuadro, cuadro):
    response = cliente_cuadro.post(REQUESTS_URL, _solicitud_payload(), format="json")
    assert response.status_code == 201, response.content
    return VisitRequest.objects.get(uuid=response.json()["uuid"])


@pytest.mark.django_db
class TestFlujoVisitas:
    def test_cuadro_crea_solicitud(self, solicitud, cuadro):
        assert solicitud.status == VisitRequest.Status.PENDING
        assert solicitud.requester == cuadro
        assert solicitud.code.startswith("VIS-")

    def test_bandeja_pendientes_para_aprobador(self, cliente_aprobador, solicitud):
        response = cliente_aprobador.get(f"{REQUESTS_URL}pending/")
        assert response.status_code == 200
        uuids = [item["uuid"] for item in response.json()["results"]]
        assert str(solicitud.uuid) in uuids

    def test_cuadro_no_ve_bandeja_de_pendientes(self, cliente_cuadro, solicitud):
        response = cliente_cuadro.get(f"{REQUESTS_URL}pending/")
        assert response.status_code == 403

    def test_patch_estado_aprobada_genera_solapin(self, cliente_aprobador, solicitud, aprobador):
        """RF-05.7: al pasar a APROBADA se genera el solapín temporal."""
        response = cliente_aprobador.patch(
            f"{REQUESTS_URL}{solicitud.uuid}/estado/",
            {"estado": "APROBADA", "motivo": "Visita autorizada por dirección"},
            format="json",
        )
        assert response.status_code == 200, response.content
        solicitud.refresh_from_db()
        assert solicitud.status == VisitRequest.Status.APPROVED

        badge = Badge.objects.filter(notes__icontains=solicitud.code).first()
        assert badge is not None
        assert badge.access_level == "VISITANTE"
        assert badge.user is not None
        assert badge.user.tipo_usuario == "VISITANTE"

    def test_patch_estado_rechazada_requiere_motivo(self, cliente_aprobador, solicitud):
        response = cliente_aprobador.patch(
            f"{REQUESTS_URL}{solicitud.uuid}/estado/",
            {"estado": "RECHAZADA", "motivo": ""},
            format="json",
        )
        assert response.status_code == 400
        solicitud.refresh_from_db()
        assert solicitud.status == VisitRequest.Status.PENDING

    def test_patch_estado_rechazada_ok(self, cliente_aprobador, solicitud):
        response = cliente_aprobador.patch(
            f"{REQUESTS_URL}{solicitud.uuid}/estado/",
            {"estado": "RECHAZADA", "motivo": "Periodo no apto"},
            format="json",
        )
        assert response.status_code == 200
        solicitud.refresh_from_db()
        assert solicitud.status == VisitRequest.Status.REJECTED

    def test_cuadro_no_puede_aprobar(self, cliente_cuadro, solicitud):
        response = cliente_cuadro.patch(
            f"{REQUESTS_URL}{solicitud.uuid}/estado/",
            {"estado": "APROBADA"},
            format="json",
        )
        assert response.status_code == 403
