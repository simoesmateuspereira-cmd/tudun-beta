from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from audit.models import AuditEvent
from communities.models import Community, Membership


class MFARecoveryCommandTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "admin_recuperacao",
            "admin.recuperacao@example.invalid",
            "Senha-Ficticia-123",
            is_superuser=True,
        )
        self.totp = TOTPDevice.objects.create(user=self.user, name="Autenticador", confirmed=True)
        self.recovery = StaticDevice.objects.create(user=self.user, name="Recuperação", confirmed=True)
        self.recovery.token_set.create(token="123456")

    def test_reset_requires_explicit_confirmation(self):
        with self.assertRaises(CommandError):
            call_command("reset_admin_mfa", self.user.username, confirm="NAO")
        self.assertTrue(TOTPDevice.objects.filter(user=self.user).exists())
        self.assertTrue(StaticDevice.objects.filter(user=self.user).exists())

    def test_reset_removes_factors_and_leaves_audit_without_secrets(self):
        call_command("reset_admin_mfa", self.user.username, confirm="REDEFINIR")
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())
        self.assertFalse(StaticDevice.objects.filter(user=self.user).exists())
        event = AuditEvent.objects.get(action="identity.mfa_reset", target_id=str(self.user.pk))
        self.assertEqual(event.details, {})

    def test_reissue_recovery_invalidates_previous_codes(self):
        community = Community.objects.create(name="Recuperação", slug="recuperacao", created_by=self.user)
        Membership.objects.create(
            community=community,
            user=self.user,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
        )
        self.client.force_login(self.user)
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = self.totp.persistent_id
        session.save()
        response = self.client.post(reverse("identity:mfa_reissue"))
        self.assertRedirects(response, reverse("identity:mfa_recovery"))
        self.assertFalse(StaticDevice.objects.filter(pk=self.recovery.pk).exists())
        self.assertEqual(len(self.client.session["mfa_recovery_codes"]), 10)
