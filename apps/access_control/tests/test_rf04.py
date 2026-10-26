"""Pruebas del motor de verificación y registro de acceso (RF-04)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import AccessLog
from apps.access_control.services import DenialReason, verificar_acceso
from apps.solapines.models import Badge
from apps.solapines.services import generar_solapin

VERIFY_URL = "/api/v1/access_control/verify/"
REGISTER_URL = "/api/v1/access_control/register/"


@pytest.fixture
def estudiante(django_user_model):
    user = django_user_model.objects.create_user(
        username="est.rf04",
        password="x",
        nombres="Diosbel",
        apellidos="Tamayo",
        ci="03051234567",
        tipo_usuario="ESTUDIANTE",
        role="STUDENT",
        foto="badges/photos/diosbel.jpg",
    )
    badge, _ = generar_solapin(user)
    return user, badge


@pytest.fixture
def seguridad(django_user_model):
    return django_user_model.objects.create_user(
        username="seg.rf04", password="x", role="SEG", tipo_usuario="TRABAJADOR"
    )


@pytest.mark.django_db
class TestMotorVerificacion:
    def test_solapin_cancelado_deniega_siempre(self, estudiante):
        """Regla 2: un solapín cancelado NUNCA permite el acceso."""
        user, badge = estudiante
        badge.cancel(reason="Extraviado")

        result = verificar_acceso(str(badge.codigo_qr))

        assert result.allowed is False
        assert result.reason == DenialReason.BADGE_CANCELLED

    def test_deniega_por_ci_tambien_si_esta_cancelado(self, estudiante):
        user, badge = estudiante
        badge.cancel(reason="Extraviado")

        assert verificar_acceso(user.ci).allowed is False

    def test_permite_solapin_activo(self, estudiante):
        user, badge = estudiante
        result = verificar_acceso(str(badge.codigo_qr))

        assert result.allowed is True
        assert result.reason == ""

    def test_acepta_payload_json_del_qr(self, estudiante):
        user, badge = estudiante
        assert verificar_acceso(badge.qr_payload).allowed is True

    def test_busca_por_ci(self, estudiante):
        user, badge = estudiante
        result = verificar_acceso("03051234567")
        assert result.allowed is True
        assert result.badge.pk == badge.pk

    def test_identificador_inexistente_deniega(self, db):
        result = verificar_acceso("00000000000")
        assert result.allowed is False
        assert result.reason == DenialReason.NOT_FOUND

    def test_visitante_vencido_deniega(self, django_user_model):
        """Regla 3: el solapín de visitante sólo vale dentro de su vigencia."""
        visitante = django_user_model.objects.create_user(
            username="vis.rf04", password="x", tipo_usuario="VISITANTE", role="STUDENT"
        )
        badge, _ = generar_solapin(visitante)
        badge.expires_at = timezone.now() - timedelta(hours=1)
        badge.save(update_fields=["expires_at"])

        result = verificar_acceso(str(badge.codigo_qr))

        assert result.allowed is False
        assert result.reason == DenialReason.BADGE_EXPIRED

    def test_estado_vencido_deniega(self, estudiante):
        user, badge = estudiante
        badge.status = Badge.Status.EXPIRED
        badge.save(update_fields=["status"])

        assert verificar_acceso(str(badge.codigo_qr)).allowed is False

    def test_usuario_inactivo_deniega(self, estudiante):
        user, badge = estudiante
        user.estado = False
        user.save(update_fields=["estado"])

        result = verificar_acceso(str(badge.codigo_qr))
        assert result.allowed is False
        assert result.reason == DenialReason.USER_INACTIVE


@pytest.mark.django_db
class TestEndpointsRF04:
    def test_verify_exitoso(self, estudiante, seguridad):
        user, badge = estudiante
        client = APIClient()
        client.force_authenticate(user=seguridad)

        response = client.post(VERIFY_URL, {"identificador": str(badge.codigo_qr)}, format="json")

        assert response.status_code == 200
        assert response.data["permitido"] is True
        assert response.data["datos_persona"]["nombre"] == "Diosbel Tamayo"
        assert response.data["datos_persona"]["nivel"] == "Estudiante"
        assert response.data["solapin"]["estado"] == "ACTIVO"
        # La verificación no registra movimientos.
        assert AccessLog.objects.count() == 0

    def test_verify_denegado(self, estudiante, seguridad):
        user, badge = estudiante
        badge.cancel(reason="Baja")
        client = APIClient()
        client.force_authenticate(user=seguridad)

        response = client.post(VERIFY_URL, {"identificador": user.ci}, format="json")

        assert response.status_code == 200
        assert response.data["permitido"] is False
        assert response.data["razon"] == "SOLAPIN_CANCELADO"

    def test_verify_requiere_rol_de_seguridad(self, estudiante):
        user, badge = estudiante
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(VERIFY_URL, {"identificador": str(badge.codigo_qr)}, format="json")

        assert response.status_code == 403

    def test_register_crea_registro(self, estudiante, seguridad):
        user, badge = estudiante
        client = APIClient()
        client.force_authenticate(user=seguridad)

        response = client.post(
            REGISTER_URL,
            {"solapin": str(badge.codigo_qr), "tipo_movimiento": "ENTRADA"},
            format="json",
        )

        assert response.status_code == 201
        log = AccessLog.objects.get()
        assert log.result == AccessLog.Result.GRANTED
        assert log.movement == "ENTRADA"
        assert log.registered_by == seguridad
        assert log.badge == badge

    def test_register_denegado_no_crea_entrada(self, estudiante, seguridad):
        user, badge = estudiante
        badge.cancel(reason="Baja")
        client = APIClient()
        client.force_authenticate(user=seguridad)

        response = client.post(
            REGISTER_URL,
            {"solapin": str(badge.codigo_qr), "tipo_movimiento": "ENTRADA"},
            format="json",
        )

        assert response.status_code == 403
        log = AccessLog.objects.get()
        assert log.result == AccessLog.Result.DENIED
        assert log.denial_reason == "SOLAPIN_CANCELADO"

    def test_register_solo_seguridad(self, estudiante):
        user, badge = estudiante
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            REGISTER_URL,
            {"solapin": str(badge.codigo_qr), "tipo_movimiento": "ENTRADA"},
            format="json",
        )

        assert response.status_code == 403
        assert AccessLog.objects.count() == 0
