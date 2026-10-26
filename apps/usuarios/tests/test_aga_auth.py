"""Pruebas del servicio mock de AGA_AUTH y del login federado."""

from __future__ import annotations

import pytest

from apps.usuarios.models import User
from apps.usuarios.services import AgaAuthClient, AgaAuthError

pytestmark = pytest.mark.django_db


class TestAgaAuthClient:
    def test_mock_devuelve_perfil(self):
        perfil = AgaAuthClient().authenticate("juan.perez", "cualquier-clave")
        assert perfil["username"] == "juan.perez"
        assert perfil["dni"]
        assert perfil["nombres"]
        assert perfil["tipo_usuario"] == "Trabajador"

    def test_credenciales_vacias_fallan(self):
        with pytest.raises(AgaAuthError):
            AgaAuthClient().authenticate("", "")

    def test_modo_real_sin_url_configurada(self, settings):
        settings.AGA_AUTH_MODE = "real"
        with pytest.raises(AgaAuthError):
            AgaAuthClient().authenticate("x", "y")

    def test_modo_desconocido_trata_como_real(self, settings):
        settings.AGA_AUTH_MODE = "typo"
        with pytest.raises(AgaAuthError):
            AgaAuthClient().authenticate("x", "y")


class TestAgaAuthLoginView:
    URL = "/api/v1/auth/login/aga/"

    def test_crea_usuario_y_devuelve_jwt(self, client):
        response = client.post(
            self.URL, {"username": "nuevo.usuario", "password": "clave123"}, format="json"
        )
        assert response.status_code == 200, response.data
        assert response.data["access"]
        assert response.data["refresh"]
        assert response.data["aga_auth"]["creado"] is True
        assert response.data["aga_auth"]["modo"] == "mock"

        user = User.objects.get(username="nuevo.usuario")
        assert user.tipo_usuario == "TRABAJADOR"
        assert user.sync_source == "AGA_AUTH"
        assert user.ci == "91050612345"

    def test_segunda_vez_actualiza_sin_crear(self, client):
        client.post(self.URL, {"username": "re.current", "password": "x"}, format="json")
        response = client.post(self.URL, {"username": "re.current", "password": "x"}, format="json")
        assert response.status_code == 200
        assert response.data["aga_auth"]["creado"] is False
        assert User.objects.filter(username="re.current").count() == 1

    def test_me_con_el_token(self, client, django_user_model):
        tokens = client.post(self.URL, {"username": "me.test", "password": "x"}, format="json").data
        access = tokens["access"]
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {access}"
        me = client.get("/api/v1/auth/me/")
        assert me.status_code == 200, me.data
        assert me.data["username"] == "me.test"
        assert "permissions" in me.data
