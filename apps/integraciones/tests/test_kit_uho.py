"""Pruebas de la integración del ``uho-auth-kit`` (backend).

El kit solo llama a la red cuando ``AGA_AUTH_TOKEN`` está definido y el modo es
real; aquí se simula ``requests.post`` para no depender de ``auth.uho.edu.cu``.
"""

from unittest import mock

from django.test import TestCase, override_settings

from apps.integraciones.kit_uho import kit_disponible, uho_login
from apps.integraciones.kit_uho.uho_auth.client import _aga_config


class UhoAuthKitTests(TestCase):
    def test_client_reads_aga_auth_configuration_from_settings(self):
        with override_settings(
            UHO_INTEGRATIONS={
                "AGA_AUTH": {
                    "enabled": True,
                    "base_url": "https://auth.uho.edu.cu",
                    "token": "token-de-prueba",
                    "origin": "https://auth.uho.edu.cu",
                    "timeout": 5,
                }
            }
        ):
            config = _aga_config()
            self.assertTrue(config["enabled"])
            self.assertEqual(config["base_url"], "https://auth.uho.edu.cu")

    @mock.patch("apps.integraciones.kit_uho.uho_auth.client.requests.post")
    def test_uho_login_normalizes_profile(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {
            "OK": True,
            "activeUser": {
                "uid": "juan.perez",
                "account_state": "TRUE",
                "personal_information": {
                    "given_name": "Juan",
                    "sn": "Pérez",
                    "dni": "85042312345",
                    "mail": "juan.perez@uho.edu.cu",
                },
                "account_info": {"user_type": "Trabajador"},
            },
        }
        with override_settings(
            UHO_INTEGRATIONS={
                "AGA_AUTH": {
                    "enabled": True,
                    "base_url": "https://auth.uho.edu.cu",
                    "token": "token-de-prueba",
                    "origin": "https://auth.uho.edu.cu",
                    "timeout": 5,
                }
            }
        ):
            perfil = uho_login("juan.perez", "clave")

        self.assertEqual(perfil["username"], "juan.perez")
        self.assertEqual(perfil["nombres"], "Juan")
        self.assertEqual(perfil["dni"], "85042312345")
        self.assertEqual(perfil["tipo_usuario"], "Trabajador")
        self.assertTrue(perfil["active"])
        # El contrato de red se mantiene: POST {base}/login con Authorization AGA.
        self.assertEqual(post.call_args.args[0], "https://auth.uho.edu.cu/login")
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "AGA token-de-prueba")

    def test_uho_login_without_token_raises(self):
        with override_settings(
            UHO_INTEGRATIONS={"AGA_AUTH": {"enabled": True, "base_url": "", "token": ""}}
        ), mock.patch.dict("os.environ", {"AGA_AUTH_TOKEN": "", "UHO_API_KEY": ""}):
            with self.assertRaises(RuntimeError):
                uho_login("usuario", "clave")

    def test_kit_flag_is_disabled_by_default(self):
        with mock.patch.dict("os.environ", {"UHO_KIT_ENABLED": "false"}):
            self.assertFalse(kit_disponible())
        with mock.patch.dict("os.environ", {"UHO_KIT_ENABLED": "true"}):
            self.assertTrue(kit_disponible())
