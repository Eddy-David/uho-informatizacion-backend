"""Pruebas de integración del registro unificado en LogAuditoria (Sección 6)."""

from __future__ import annotations

import json

import pytest
from django.test import RequestFactory
from rest_framework.test import APIClient

from apps.auditoria.models import LogAuditoria
from apps.core.middleware import RequestAuditMiddleware, _sanitize


@pytest.mark.django_db
class TestSanitize:
    def test_oculta_password(self):
        assert _sanitize({"password": "x", "user": "a"}) == {"password": "***", "user": "a"}

    def test_recursivo(self):
        data = {"user": {"password": "x", "token": "y"}, "list": [{"api_key": "z"}]}
        assert _sanitize(data)["user"]["password"] == "***"
        assert _sanitize(data)["list"][0]["api_key"] == "***"


@pytest.mark.django_db
class TestLogAuditoria:
    def test_registro_post(self, django_user_model):
        middleware = RequestAuditMiddleware(lambda r: type("R", (), {"status_code": 201})())
        request = RequestFactory().post(
            "/api/v1/visitors/",
            data=json.dumps({"nombre": "Ana", "password": "secreto"}),
            content_type="application/json",
            REMOTE_ADDR="10.0.0.5",
        )
        request.user = django_user_model.objects.create_user(username="op", password="x")
        response = type("R", (), {"status_code": 201})()
        middleware._maybe_audit(request, response, 120)

        log = LogAuditoria.objects.get()
        assert log.accion == "POST"
        assert log.usuario == request.user
        assert log.detalle["cuerpo"]["password"] == "***"
        assert log.detalle["cuerpo"]["nombre"] == "Ana"
        assert log.status_code == 201

    def test_get_no_registra(self):
        request = RequestFactory().get("/api/v1/visitors/")
        RequestAuditMiddleware._maybe_audit(request, type("R", (), {"status_code": 200})(), 10)
        assert LogAuditoria.objects.count() == 0

    def test_salud_no_registra(self):
        request = RequestFactory().post("/api/v1/health/")
        RequestAuditMiddleware._maybe_audit(request, type("R", (), {"status_code": 200})(), 10)
        assert LogAuditoria.objects.count() == 0

    def test_registro_inmutable(self):
        log = LogAuditoria.objects.create(modulo="api", accion="POST")
        with pytest.raises(ValueError):
            log.save()
        with pytest.raises(ValueError):
            log.delete()


@pytest.mark.django_db
class TestLogAuditoriaIntegracion:
    """Cadena real middleware + DRF: el caso que fallaba por RawPostDataException."""

    def test_login_exitoso_registra_log(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="operador", password="ClaveSegura2026*"
        )
        client = APIClient()

        response = client.post(
            "/api/v1/auth/login/",
            {"username": "operador", "password": "ClaveSegura2026*"},
            format="json",
            HTTP_USER_AGENT="pytest-auditoria",
        )

        assert response.status_code == 200, response.content
        log = LogAuditoria.objects.get(ruta="/api/v1/auth/login/")
        assert log.accion == "POST"
        assert log.status_code == 200
        assert log.method == "POST"
        assert log.usuario == user
        assert log.detalle["cuerpo"]["username"] == "operador"
        assert log.detalle["cuerpo"]["password"] == "***"
        assert log.request_id
        assert log.user_agent == "pytest-auditoria"

    def test_post_autenticado_registra_log_y_usuario(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="operador", password="ClaveSegura2026*"
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch(
            "/api/v1/auth/me/",
            {"phone": "55512345"},
            format="json",
        )

        assert response.status_code == 200, response.content
        log = LogAuditoria.objects.get(ruta="/api/v1/auth/me/")
        assert log.status_code == 200
        assert log.usuario == user
        assert log.detalle["cuerpo"] == {"phone": "55512345"}
