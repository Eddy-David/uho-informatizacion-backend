"""Pruebas del Solapín Digital (RF-03)."""

from __future__ import annotations

import json

import pytest
from rest_framework.test import APIClient

from apps.solapines.models import Badge
from apps.solapines.services import generar_solapin, nivel_acceso_por_defecto


@pytest.mark.django_db
class TestNivelAccesoPorDefecto:
    """RF-03.7 — niveles por defecto según el tipo de usuario."""

    @pytest.mark.parametrize(
        ("user_type", "esperado"),
        [
            ("CUADRO", "LIBRE"),
            ("PROFESOR", "PERMANENTE"),
            ("TRABAJADOR", "LIMITADO"),
            ("ESTUDIANTE", "ESTUDIANTE"),
            ("VISITANTE", "VISITANTE"),
        ],
    )
    def test_niveles_oficiales(self, user_type, esperado):
        assert nivel_acceso_por_defecto(user_type) == esperado


@pytest.mark.django_db
class TestGenerarSolapin:
    def test_asigna_nivel_y_uuid(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="profe", password="x", tipo_usuario="PROFESOR"
        )
        badge, creado = generar_solapin(user)

        assert creado is True
        assert badge.access_level == "PERMANENTE"
        assert badge.status == Badge.Status.ACTIVE
        assert badge.codigo_qr is not None
        assert user.access_level == "PERMANENTE"

    def test_es_idempotente(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="est", password="x", tipo_usuario="ESTUDIANTE"
        )
        primero, _ = generar_solapin(user)
        segundo, creado = generar_solapin(user)

        assert creado is False
        assert primero.pk == segundo.pk
        assert Badge.objects.filter(user=user).count() == 1

    def test_qr_solo_uuid_y_estado(self, django_user_model):
        """RF-03.9 — el QR no puede contener datos personales."""
        user = django_user_model.objects.create_user(
            username="ana",
            password="x",
            nombres="Ana",
            apellidos="Pérez",
            tipo_usuario="ESTUDIANTE",
            ci="99010112345",
        )
        badge, _ = generar_solapin(user)
        payload = json.loads(badge.qr_payload)

        assert set(payload) == {"uuid", "estado"}
        assert payload["uuid"] == str(badge.codigo_qr)
        assert payload["estado"] == "ACTIVO"
        for dato in ("Ana", "Pérez", "99010112345", user.username):
            assert dato not in badge.qr_payload


@pytest.mark.django_db
class TestEndpoints:
    def test_my_solapin_genera_si_no_existe(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="nuevo", password="x", tipo_usuario="TRABAJADOR"
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/solapines/my-solapin/")

        assert response.status_code == 201
        assert response.data["access_level"] == "LIMITADO"
        assert response.data["codigo_qr"]

        otra = client.get("/api/v1/solapines/my-solapin/")
        assert otra.status_code == 200
        assert otra.data["codigo_qr"] == response.data["codigo_qr"]

    def test_cancel_solo_administradores(self, django_user_model):
        dueno = django_user_model.objects.create_user(
            username="dueno", password="x", tipo_usuario="ESTUDIANTE", role="STUDENT"
        )
        dsp = django_user_model.objects.create_user(username="dsp", password="x", role="DSP")
        badge, _ = generar_solapin(dueno)
        url = f"/api/v1/solapines/badges/{badge.uuid}/cancel/"

        client = APIClient()
        client.force_authenticate(user=dueno)
        assert client.patch(url, {"reason": "x"}, format="json").status_code == 403

        client.force_authenticate(user=dsp)
        response = client.patch(url, {"reason": "Baja"}, format="json")
        assert response.status_code == 200
        assert response.data["status"] == Badge.Status.CANCELLED

    def test_qr_png_propio(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="qr", password="x", tipo_usuario="ESTUDIANTE"
        )
        badge, _ = generar_solapin(user)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/solapines/badges/{badge.uuid}/qr/")

        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"
        assert response.content.startswith(b"\x89PNG")


@pytest.mark.django_db
class TestImagenSolapin:
    """RF-03.3 — composición plantilla + datos + QR con Pillow."""

    @staticmethod
    def _crear_plantilla(user_type="ESTUDIANTE", imagen=False):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from apps.solapines.models import BadgeTemplate

        kwargs = {"name": f"Plantilla {user_type}", "user_type": user_type, "is_default": True}
        if imagen:
            buffer = BytesIO()
            Image.new("RGB", (600, 380), (240, 240, 240)).save(buffer, format="PNG")
            kwargs["background_image"] = SimpleUploadedFile(
                "base.png", buffer.getvalue(), content_type="image/png"
            )
        return BadgeTemplate.objects.create(**kwargs)

    def test_compone_png_con_plantilla(self, django_user_model):
        from PIL import Image

        self._crear_plantilla(imagen=True)
        user = django_user_model.objects.create_user(
            username="comp",
            password="x",
            nombres="Lucía",
            apellidos="Gómez",
            tipo_usuario="ESTUDIANTE",
            ci="99020211223",
        )
        badge, _ = generar_solapin(user)

        from apps.solapines.compositor import compose_badge_image

        png = compose_badge_image(badge)

        assert png.startswith(b"\x89PNG")
        # Respeta el tamaño de la plantilla subida por el administrador.
        assert Image.open(BytesIO_(png)).size == (600, 380)

    def test_compone_sin_plantilla_ni_foto(self, django_user_model):
        from apps.solapines.compositor import compose_badge_image

        user = django_user_model.objects.create_user(
            username="sinplantilla", password="x", tipo_usuario="PROFESOR"
        )
        badge, _ = generar_solapin(user)
        png = compose_badge_image(badge)

        assert png.startswith(b"\x89PNG")

    def test_endpoint_mio_imagen(self, django_user_model):
        self._crear_plantilla()
        user = django_user_model.objects.create_user(
            username="mio", password="x", tipo_usuario="ESTUDIANTE"
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/solapines/mio/imagen/")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"
        assert response.content.startswith(b"\x89PNG")
        assert "inline" in response["Content-Disposition"]

        descarga = client.get("/api/v1/solapines/mio/imagen/?download=1")
        assert "attachment" in descarga["Content-Disposition"]
        assert ".png" in descarga["Content-Disposition"]

    def test_endpoint_requiere_autenticacion(self):
        response = APIClient().get("/api/v1/solapines/mio/imagen/")
        assert response.status_code == 401

    def test_descarga_usa_el_numero_del_solapin(self, django_user_model):
        """RF-02.3: el archivo descargado se nombra con el dato de la base."""
        self._crear_plantilla()
        user = django_user_model.objects.create_user(
            username="descarga", password="x", tipo_usuario="ESTUDIANTE"
        )
        badge, _ = generar_solapin(user)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/solapines/mio/imagen/?download=1")

        assert badge.badge_number in response["Content-Disposition"]


def BytesIO_(data):
    """Atajo para abrir bytes como imagen Pillow dentro de las pruebas."""
    from io import BytesIO

    return BytesIO(data)
