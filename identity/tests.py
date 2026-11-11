from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from communities.models import Community, Membership


class MFATests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin_mfa", "admin.mfa@example.invalid", "Senha-Ficticia-123")
        self.member = User.objects.create_user("membro_mfa", "membro.mfa@example.invalid", "Senha-Ficticia-123")
        self.community = Community.objects.create(name="MFA Fictício", slug="mfa", created_by=self.admin)
        Membership.objects.create(
            community=self.community, user=self.admin, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE
        )
        Membership.objects.create(
            community=self.community, user=self.member, role=Membership.Role.MEMBER, status=Membership.Status.ACTIVE
        )

    def test_community_admin_is_redirected_to_mfa(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("communities:home"))
        self.assertRedirects(response, reverse("identity:mfa"))

    def test_superuser_is_redirected_to_mfa(self):
        self.admin.is_superuser = True
        self.admin.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("communities:home"))
        self.assertRedirects(response, reverse("identity:mfa"))

    def test_regular_member_does_not_need_mfa(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("communities:home")).status_code, 200)

    def test_recovery_code_verifies_admin_and_is_single_use(self):
        TOTPDevice.objects.create(user=self.admin, name="Autenticador", confirmed=True)
        recovery = StaticDevice.objects.create(user=self.admin, name="Recuperação", confirmed=True)
        token = recovery.token_set.create(token="123456")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("identity:mfa"), {"token": "123456"})
        self.assertRedirects(response, reverse("communities:home"))
        self.assertEqual(self.client.get(reverse("communities:home")).status_code, 200)
        self.assertFalse(recovery.token_set.filter(pk=token.pk).exists())

    def test_first_mfa_access_offers_setup_without_leaking_existing_secret(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("identity:mfa"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ative o segundo fator")
        self.assertTrue(TOTPDevice.objects.filter(user=self.admin, confirmed=False).exists())

    def test_signup_requires_unique_email_case_insensitively(self):
        response = self.client.post(
            reverse("identity:signup"),
            {
                "username": "duplicado",
                "email": "MEMBRO.MFA@example.invalid",
                "password1": "Senha-Ficticia-456",
                "password2": "Senha-Ficticia-456",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Já existe uma conta com este e-mail.")
