import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from playwright.sync_api import expect, sync_playwright

from communities.models import Community, Invitation, Membership
from communities.services import create_invitation

from .models import IdentityProfile


CHROME_PATH = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
PASSWORD = "Senha-Ficticia-123"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CriticalJourneysE2ETests(StaticLiveServerTestCase):
    """Jornadas críticas executadas no Chrome, sem navegador adicional."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not CHROME_PATH.is_file():
            raise RuntimeError(f"Chrome não encontrado em {CHROME_PATH}")
        # O driver síncrono do Playwright usa um loop interno que o Django detecta.
        # Esta exceção fica restrita ao processo de testes E2E.
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=str(CHROME_PATH),
            headless=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin_e2e", "admin.e2e@example.invalid", PASSWORD)
        self.moderator = User.objects.create_user("moderador_e2e", "mod.e2e@example.invalid", PASSWORD)
        self.member = User.objects.create_user("membro_e2e", "membro.e2e@example.invalid", PASSWORD)
        self.applicant = User.objects.create_user("candidato_e2e", "candidato.e2e@example.invalid", PASSWORD)
        for user in (self.admin, self.moderator, self.member, self.applicant):
            IdentityProfile.objects.create(user=user, email_verified_at=timezone.now())
        self.community = Community.objects.create(name="Alfa E2E", slug="alfa-e2e", created_by=self.admin)
        self.other = Community.objects.create(name="Beta E2E", slug="beta-e2e", created_by=self.admin)
        for user, role in (
            (self.admin, Membership.Role.ADMIN),
            (self.moderator, Membership.Role.MODERATOR),
            (self.member, Membership.Role.MEMBER),
        ):
            Membership.objects.create(
                community=self.community,
                user=user,
                role=role,
                status=Membership.Status.ACTIVE,
                joined_at=timezone.now(),
            )
        Membership.objects.create(
            community=self.other,
            user=self.admin,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            joined_at=timezone.now(),
        )
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000})
        self.page = self.context.new_page()
        self.page.set_default_timeout(10000)

    def tearDown(self):
        self.context.close()

    def url(self, route, *args):
        return self.live_server_url + reverse(route, args=args)

    def login(self, username):
        self.page.goto(self.url("identity:login"))
        self.page.locator('input[name="username"]').fill(username)
        self.page.locator('input[name="password"]').fill(PASSWORD)
        self.page.get_by_role("button", name="Entrar", exact=True).click()

    def test_admin_configures_mfa_recovery_codes_and_creates_invitation(self):
        self.login(self.admin.username)
        expect(self.page).to_have_url(self.url("identity:mfa"))
        expect(self.page.get_by_role("heading", name="Ative o segundo fator")).to_be_visible()

        setup_device = TOTPDevice.objects.get(user=self.admin, confirmed=False)
        self.page.locator('input[name="token"]').fill(f"{totp(setup_device.bin_key):06d}")
        self.page.get_by_role("button", name="Ativar MFA").click()

        expect(self.page).to_have_url(self.url("identity:mfa_recovery"))
        codes = self.page.locator(".recovery-codes code").all_inner_texts()
        self.assertEqual(len(codes), 10)
        self.assertEqual(len(set(codes)), 10)
        self.page.get_by_role("button", name="Confirmei que guardei os códigos").click()
        expect(self.page).to_have_url(self.url("communities:home"))

        self.page.goto(self.url("communities:invitations", self.community.slug))
        self.page.locator('input[name="email"]').fill(self.applicant.email)
        self.page.locator('select[name="role"]').select_option(Membership.Role.MEMBER)
        self.page.get_by_role("button", name="Criar convite").click()

        expect(self.page.get_by_text("Convite criado", exact=False)).to_be_visible()
        invitation = Invitation.objects.get(community=self.community, email=self.applicant.email)
        self.assertEqual(invitation.state, "pendente")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.applicant.email])
        self.assertIn("/convites/", mail.outbox[0].body)

    def test_invited_user_accepts_and_cannot_access_another_community(self):
        invitation, raw_token = create_invitation(
            community=self.community,
            email=self.applicant.email,
            role=Membership.Role.MEMBER,
            created_by=self.admin,
        )
        self.login(self.applicant.username)
        expect(self.page).to_have_url(self.url("communities:home"))

        self.page.goto(self.url("communities:accept_invitation", raw_token))
        self.page.get_by_role("button", name="Confirmar aceite").click()
        expect(self.page).to_have_url(self.url("communities:detail", self.community.slug))
        expect(self.page.get_by_role("heading", name=self.community.name)).to_be_visible()

        invitation.refresh_from_db()
        self.assertEqual(invitation.accepted_by, self.applicant)
        membership = Membership.objects.get(community=self.community, user=self.applicant)
        self.assertEqual(membership.status, Membership.Status.ACTIVE)

        response = self.page.goto(self.url("communities:detail", self.other.slug))
        self.assertEqual(response.status, 403)

    def test_member_creates_open_invite_link_but_cannot_access_audit(self):
        self.login(self.member.username)
        self.page.goto(self.url("communities:invitations", self.community.slug))
        expect(self.page.get_by_text("2 convites", exact=False)).to_be_visible()
        self.page.locator('select[name="role"]').select_option(Membership.Role.MEMBER)
        self.page.get_by_role("button", name="Criar convite").click()

        expect(self.page.get_by_text("Convite criado", exact=False)).to_be_visible()
        invitation = Invitation.objects.get(community=self.community, created_by=self.member)
        self.assertEqual(invitation.state, "pendente")
        expect(self.page.get_by_text("Link do último convite", exact=False)).to_be_visible()
        expect(self.page.locator(".invite-link code")).to_contain_text("/convites/")

        response = self.page.goto(self.url("communities:audit", self.community.slug))
        self.assertEqual(response.status, 403)

    def test_signup_via_invite_and_email_verification_run_in_browser_with_static_assets(self):
        css_response = self.page.request.get(self.live_server_url + "/static/tudun.css")
        self.assertEqual(css_response.status, 200)
        _, raw_token = create_invitation(
            community=self.community,
            email="",
            role=Membership.Role.MEMBER,
            created_by=self.admin,
        )
        self.page.goto(f"{self.url('identity:signup')}?convite={raw_token}")
        self.page.locator('input[name="username"]').fill("nova_e2e")
        self.page.locator('input[name="email"]').fill("Nova.E2E@example.invalid")
        self.page.locator('input[name="password1"]').fill("Senha-Ficticia-456")
        self.page.locator('input[name="password2"]').fill("Senha-Ficticia-456")
        self.page.get_by_role("button", name="Criar conta e entrar", exact=True).click()

        expect(self.page).to_have_url(self.url("communities:detail", self.community.slug))
        membership = Membership.objects.get(community=self.community, user__username="nova_e2e")
        self.assertEqual(membership.status, Membership.Status.ACTIVE)
        self.assertEqual(len(mail.outbox), 1)
        verification_url = mail.outbox[0].body.split("Acesse: ", 1)[1].splitlines()[0]
        self.page.goto(verification_url)
        expect(self.page.get_by_text("E-mail confirmado com sucesso.", exact=False)).to_be_visible()
        user = get_user_model().objects.get(username="nova_e2e")
        self.assertEqual(user.email, "nova.e2e@example.invalid")
        self.assertIsNotNone(user.identity_profile.email_verified_at)

    def test_signup_page_without_invite_shows_closed_message(self):
        self.page.goto(self.url("identity:signup"))
        expect(self.page.get_by_role("heading", name="Entrada somente por convite")).to_be_visible()
