"""Pruebas del comando ``seed_data`` (arranque de un entorno nuevo).

Garantiza el "comando mágico" del README: con la base de datos ya migrada
(el runner de pruebas crea las tablas), ``seed_data`` deja el sistema listo
para usarse — roles, sedes, usuarios demo y datos para el dashboard — y puede
ejecutarse de nuevo sin duplicar registros.
"""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.access_control.models import AccessLog
from apps.core.catalogs import AccessPoint, CampusSite
from apps.solapines.models import Badge
from apps.usuarios.constants import RoleCode
from apps.usuarios.models import RoleDefinition, User

DEMO_ROLES = {"SA", "ADM", "DSP", "SEG", "AV", "CUADRO", "EST", "PROF"}


class SeedDataCommandTests(TestCase):
    def _seed(self, *args):
        out = StringIO()
        # ``--no-migrate``: las pruebas ya corren dentro de una transacción con
        # las tablas creadas.
        call_command("seed_data", "--no-migrate", *args, stdout=out)
        return out.getvalue()

    def test_seed_data_creates_roles_campuses_and_demo_users(self):
        self._seed()

        roles = set(RoleDefinition.objects.values_list("code", flat=True))
        self.assertTrue(DEMO_ROLES.issubset(roles), f"Faltan roles: {DEMO_ROLES - roles}")
        self.assertEqual(roles, set(RoleCode.values))

        self.assertEqual(CampusSite.objects.count(), 4)
        self.assertGreaterEqual(AccessPoint.objects.count(), 4)

        demo = User.objects.filter(role__in=DEMO_ROLES)
        self.assertEqual(set(demo.values_list("role", flat=True)), DEMO_ROLES)
        for user in demo:
            self.assertTrue(
                user.check_password("Sigacu2026*"),
                f"{user.username} no puede iniciar sesión con la clave demo",
            )

    def test_seed_data_fills_dashboard(self):
        self._seed()

        self.assertGreater(AccessLog.objects.count(), 100)
        self.assertGreater(Badge.objects.count(), 0)
        # Todo solapín demo debe tener plantilla (RF-03.1).
        self.assertFalse(Badge.objects.filter(template__isnull=True).exists())

    def test_seed_data_is_idempotent(self):
        self._seed()
        roles_1 = RoleDefinition.objects.count()
        users_1 = User.objects.count()
        logs_1 = AccessLog.objects.count()
        badges_1 = Badge.objects.count()

        self._seed()

        self.assertEqual(RoleDefinition.objects.count(), roles_1)
        self.assertEqual(User.objects.count(), users_1)
        self.assertEqual(AccessLog.objects.count(), logs_1)
        self.assertEqual(Badge.objects.count(), badges_1)

    def test_reset_recreates_demo_data(self):
        self._seed()
        users_1 = User.objects.count()
        logs_1 = AccessLog.objects.count()

        self._seed("--reset")

        self.assertEqual(User.objects.count(), users_1)
        self.assertGreater(AccessLog.objects.count(), 0)
        self.assertLessEqual(AccessLog.objects.count(), logs_1 + 60)

    def test_no_demo_skips_sample_records(self):
        self._seed("--no-demo")

        self.assertGreater(User.objects.count(), 0)
        self.assertEqual(AccessLog.objects.count(), 0)
