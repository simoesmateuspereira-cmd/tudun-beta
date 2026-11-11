import logging
import re
import time
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from communities.models import Community, Membership
from communities.services import create_invitation

from .logging import RedactSensitivePathsFilter
from .models import IdentityProfile
from .services import EMAIL_VERIFICATION_SALT


PASSWORD = "Senha-Ficticia-123"


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RATELIMIT_ENABLE=False,
)
class EmailVerificationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("verificar", "Verificar@Example.Invalid", PASSWORD)

    def signup_data(self, username="novo_beta", email="Novo.Beta@Example.Invalid"):
        return {
            "username": username,
            "email": email,
            "password1": "Senha-Ficticia-456",
            "password2": "Senha-Ficticia-456",
        }

    def test_signup_normalizes_email_sends_link_and_verifies_account(self):
        response = self.client.post(reverse("identity:signup"), self.signup_data())
        self.assertRedirects(response, reverse("identity:verification_pending"))
        user = get_user_model().objects.get(username="novo_beta")
        self.assertEqual(user.email, "novo.beta@example.invalid")
        self.assertIsNone(user.identity_profile.email_verified_at)
        self.assertEqual(len(mail.outbox), 1)
        match = re.search(r"Acesse: (\S+)", mail.outbox[0].body)
        self.assertIsNotNone(match)

        response = self.client.get(match.group(1), follow=True)
        self.assertContains(response, "E-mail confirmado com sucesso.")
        user.identity_profile.refresh_from_db()
        self.assertIsNotNone(user.identity_profile.email_verified_at)

    def test_expired_verification_link_is_rejected(self):
        token = signing.dumps(
            {"user_id": self.user.pk, "email": self.user.email.lower()},
            salt=EMAIL_VERIFICATION_SALT,
            compress=True,
        )
        with mock.patch("django.core.signing.time.time", return_value=time.time() + 172801):
            response = self.client.get(reverse("identity:verify_email", args=[token]), follow=True)
        self.assertContains(response, "link de verificação expirou")
        self.assertFalse(IdentityProfile.objects.filter(user=self.user, email_verified_at__isnull=False).exists())

    def test_tampered_verification_link_is_rejected(self):
        response = self.client.get(reverse("identity:verify_email", args=["token-adulterado"]), follow=True)
        self.assertContains(response, "link de verificação é inválido")

    def test_unverified_user_cannot_accept_invitation(self):
        community = Community.objects.create(name="Fechada", slug="fechada", created_by=self.user)
        _, raw = create_invitation(
            community=community,
            email=self.user.email,
            role=Membership.Role.MEMBER,
            created_by=self.user,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("communities:accept_invitation", args=[raw]))
        self.assertRedirects(response, reverse("identity:verification_pending"))
        self.assertFalse(Membership.objects.filter(community=community, user=self.user).exists())

    def test_database_rejects_duplicate_email_with_different_case(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user("duplicado_banco", "VERIFICAR@example.invalid", PASSWORD)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RATELIMIT_ENABLE=True,
)
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_login_returns_429_after_five_post_attempts(self):
        for attempt in range(5):
            response = self.client.post(
                reverse("identity:login"),
                {"username": "inexistente", "password": "incorreta"},
            )
            self.assertEqual(response.status_code, 200, f"Tentativa {attempt + 1}")
        response = self.client.post(
            reverse("identity:login"),
            {"username": "inexistente", "password": "incorreta"},
        )
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Muitas tentativas", status_code=429)

    def test_verification_resend_limit_does_not_send_extra_email(self):
        user = get_user_model().objects.create_user("reenvio", "reenvio@example.invalid", PASSWORD)
        self.client.force_login(user)
        for _ in range(3):
            response = self.client.post(reverse("identity:resend_verification"))
            self.assertRedirects(response, reverse("identity:verification_pending"))
        self.assertEqual(len(mail.outbox), 3)
        response = self.client.post(reverse("identity:resend_verification"))
        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), 3)


class HealthPrivacyAndLogTests(TestCase):
    def test_health_checks_database_without_disclosing_configuration(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})
        self.assertEqual(response.headers["Cache-Control"], "max-age=0, no-cache, no-store, must-revalidate, private")

    def test_health_returns_503_without_database_error_details(self):
        with mock.patch("config.views.connection.cursor", side_effect=RuntimeError("detalhe interno")):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "detalhe interno", status_code=503)
        self.assertEqual(response.json()["status"], "indisponivel")

    def test_privacy_page_states_local_retention_limits(self):
        response = self.client.get(reverse("identity:privacy"))
        self.assertContains(response, "Não há exclusão automática nesta etapa.")
        self.assertContains(response, "revisão com Karine")

    def test_access_log_redacts_invitation_and_verification_tokens(self):
        record = logging.LogRecord(
            name="django.server",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg='"GET %s HTTP/1.1"',
            args=("/convites/segredo-convite/ e /identidade/verificar-email/segredo-email/",),
            exc_info=None,
        )
        RedactSensitivePathsFilter().filter(record)
        rendered = record.getMessage()
        self.assertNotIn("segredo-convite", rendered)
        self.assertNotIn("segredo-email", rendered)
        self.assertIn("[token-oculto]", rendered)
