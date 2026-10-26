"""Pruebas de la lógica de verificación de acceso."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.access_control.models import AccessLog
from apps.access_control.services import DenialReason, verify_access
from apps.core.constants import AccessLevel, MovementType, Role, UserType
from apps.solapines.models import Badge

User = get_user_model()


class VerifyAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator = User.objects.create_user(
            username="op",
            password="x",
            nombres="Op",
            apellidos="Uno",
            role=Role.SECURITY_OFFICER,
            nivel_acceso=AccessLevel.LIMITED,
        )
        cls.student = User.objects.create_user(
            username="student",
            password="x",
            nombres="Diosbel",
            apellidos="Tamayo",
            ci="03051234567",
            tipo_usuario=UserType.STUDENT,
            nivel_acceso=AccessLevel.STUDENT,
        )
        cls.badge = Badge.objects.create(user=cls.student, access_level=AccessLevel.STUDENT)

    def test_valid_qr_grants_access_and_logs(self):
        result = verify_access(operator=self.operator, qr_token=self.badge.qr_token)
        self.assertTrue(result.allowed)
        self.assertEqual(AccessLog.objects.count(), 1)
        self.assertEqual(result.log.result, AccessLog.Result.GRANTED)

    def test_cancelled_badge_is_denied(self):
        self.badge.cancel("Reportado como extraviado")
        result = verify_access(operator=self.operator, qr_token=self.badge.qr_token)
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, DenialReason.BADGE_CANCELLED)

    def test_expired_badge_is_denied(self):
        self.badge.expires_at = timezone.now() - timedelta(days=1)
        self.badge.save(update_fields=["expires_at"])
        result = verify_access(operator=self.operator, qr_token=self.badge.qr_token)
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, DenialReason.BADGE_EXPIRED)

    def test_unknown_identity_card_is_denied(self):
        result = verify_access(operator=self.operator, identity_card="99999999999")
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, DenialReason.NOT_FOUND)
        self.assertIsNone(result.log)

    def test_search_by_identity_card(self):
        result = verify_access(
            operator=self.operator, identity_card="03051234567", movement=MovementType.EXIT
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.log.movement, MovementType.EXIT)
