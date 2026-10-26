"""Pruebas de autenticación JWT y permisos por rol."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.constants import AccessLevel, Role, UserType

User = get_user_model()


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="security",
            password="Secreta123*",
            nombres="Maité",
            apellidos="Rodríguez",
            ci="91030411098",
            role=Role.SECURITY_OFFICER,
            tipo_usuario=UserType.WORKER,
            nivel_acceso=AccessLevel.LIMITED,
        )

    def test_login_returns_jwt_and_user(self):
        response = APIClient().post(
            "/api/v1/auth/login/",
            {"username": "security", "password": "Secreta123*"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], Role.SECURITY_OFFICER)

    def test_login_with_invalid_credentials(self):
        response = APIClient().post(
            "/api/v1/auth/login/", {"username": "security", "password": "incorrecta"}, format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.data)

    def test_me_returns_profile_with_permissions(self):
        client = APIClient()
        token = client.post(
            "/api/v1/auth/login/",
            {"username": "security", "password": "Secreta123*"},
            format="json",
        ).data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access:verify", response.data["permissions"])
        self.assertNotIn("reports:view", response.data["permissions"])

    def test_logout_blacklists_refresh_token(self):
        client = APIClient()
        tokens = client.post(
            "/api/v1/auth/login/",
            {"username": "security", "password": "Secreta123*"},
            format="json",
        ).data
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = client.post(
            "/api/v1/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, 205)
