"""Pruebas base del módulo: el endpoint exige autenticación."""

from django.test import TestCase
from rest_framework.test import APIClient


class ModuleSecurityTests(TestCase):
    """Verifica que el módulo ``research`` no sea accesible de forma anónima."""

    def test_list_requires_authentication(self):
        response = APIClient().get("/api/v1/research/")
        self.assertIn(response.status_code, (401, 403))
