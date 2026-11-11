from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from audit.models import AuditEvent
from identity.models import IdentityProfile

from .models import Community, Event, Membership


class EventManagementTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("gestor-evento", "gestor.evento@example.invalid", "Senha-Ficticia-123")
        self.moderator = User.objects.create_user("moderador-evento", "mod.evento@example.invalid", "Senha-Ficticia-123")
        self.member = User.objects.create_user("membro-evento", "membro.evento@example.invalid", "Senha-Ficticia-123")
        self.outsider = User.objects.create_user("externo-evento", "externo.evento@example.invalid", "Senha-Ficticia-123")
        self.community = Community.objects.create(name="Comunidade Gestão", slug="gestao", created_by=self.admin)
        self.other = Community.objects.create(name="Outra Comunidade", slug="outra", created_by=self.admin)
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

    def payload(self, **overrides):
        start = timezone.localtime() + timedelta(days=10)
        data = {
            "title": "Encontro de Planejamento",
            "description": "Uma experiência criada pela equipe da comunidade.",
            "category": "Encontro",
            "location": "Espaço Central",
            "starts_at": start.strftime("%Y-%m-%dT%H:%M"),
            "ends_at": (start + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "capacity": 40,
            "included_in_membership": True,
            "price": "",
            "status": Event.Status.AVAILABLE,
        }
        data.update(overrides)
        return data

    def create_event(self, **overrides):
        self.client.force_login(self.moderator)
        response = self.client.post(reverse("communities:event_create", args=[self.community.slug]), self.payload(**overrides))
        self.assertEqual(response.status_code, 302)
        return Event.objects.filter(
            community=self.community,
            title=overrides.get("title", "Encontro de Planejamento"),
        ).order_by("-pk").first()

    def test_moderator_creates_and_publishes_event_with_audit(self):
        event = self.create_event()
        self.assertEqual(event.slug, "encontro-de-planejamento")
        self.assertEqual(event.created_by, self.moderator)
        self.assertEqual(str(event.price), "0.00")
        self.assertTrue(AuditEvent.objects.filter(action="event.created", target_id=str(event.pk)).exists())
        response = self.client.get(reverse("communities:events", args=[self.community.slug]))
        self.assertContains(response, event.title)

    def test_duplicate_titles_receive_distinct_stable_slugs(self):
        first = self.create_event()
        second = self.create_event()
        self.assertEqual(first.slug, "encontro-de-planejamento")
        self.assertEqual(second.slug, "encontro-de-planejamento-2")

    def test_member_and_outsider_cannot_manage_events(self):
        event = self.create_event()
        urls = (
            reverse("communities:event_create", args=[self.community.slug]),
            reverse("communities:event_update", args=[self.community.slug, event.slug]),
            reverse("communities:event_cancel", args=[self.community.slug, event.slug]),
        )
        for user in (self.member, self.outsider):
            self.client.force_login(user)
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, self.payload()).status_code, 403)

    def test_moderator_updates_without_changing_slug(self):
        event = self.create_event()
        original_slug = event.slug
        response = self.client.post(
            reverse("communities:event_update", args=[self.community.slug, event.slug]),
            self.payload(title="Encontro Atualizado", capacity=55),
        )
        self.assertRedirects(response, reverse("communities:event_detail", args=[self.community.slug, original_slug]))
        event.refresh_from_db()
        self.assertEqual(event.title, "Encontro Atualizado")
        self.assertEqual(event.capacity, 55)
        self.assertEqual(event.slug, original_slug)
        self.assertTrue(AuditEvent.objects.filter(action="event.updated", target_id=str(event.pk)).exists())

    def test_cancellation_requires_confirmation_and_preserves_record(self):
        event = self.create_event(is_featured=True)
        url = reverse("communities:event_cancel", args=[self.community.slug, event.slug])
        response = self.client.get(url)
        self.assertContains(response, "Cancelar evento")
        response = self.client.post(url)
        self.assertRedirects(response, reverse("communities:event_detail", args=[self.community.slug, event.slug]))
        event.refresh_from_db()
        self.assertEqual(event.status, Event.Status.CANCELLED)
        self.assertFalse(event.is_featured)
        self.assertTrue(AuditEvent.objects.filter(action="event.cancelled", target_id=str(event.pk)).exists())

    def test_invalid_dates_and_included_price_are_rejected(self):
        self.client.force_login(self.moderator)
        start = timezone.localtime() + timedelta(days=10)
        response = self.client.post(
            reverse("communities:event_create", args=[self.community.slug]),
            self.payload(starts_at=start.strftime("%Y-%m-%dT%H:%M"), ends_at=start.strftime("%Y-%m-%dT%H:%M")),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O término deve ser posterior ao início.")
        response = self.client.post(
            reverse("communities:event_create", args=[self.community.slug]),
            self.payload(price="25.00"),
        )
        self.assertContains(response, "Eventos incluídos na assinatura não devem ter preço adicional.")
        self.assertFalse(Event.objects.filter(community=self.community).exists())

    def test_event_from_other_community_cannot_be_edited_through_local_url(self):
        other_event = Event.objects.create(
            community=self.other,
            title="Evento Reservado",
            slug="evento-reservado",
            description="Privado",
            category="Encontro",
            location="Outro local",
            starts_at=timezone.now() + timedelta(days=5),
            ends_at=timezone.now() + timedelta(days=5, hours=2),
            capacity=20,
            created_by=self.admin,
        )
        self.client.force_login(self.moderator)
        response = self.client.post(
            reverse("communities:event_update", args=[self.community.slug, other_event.slug]),
            self.payload(title="Título indevido"),
        )
        self.assertEqual(response.status_code, 404)
        other_event.refresh_from_db()
        self.assertEqual(other_event.title, "Evento Reservado")


class CommunityProvisioningTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser("responsavel", "responsavel@example.invalid", "Senha-Ficticia-123")
        self.administrator = User.objects.create_user("novo-gestor", "novo.gestor@example.invalid", "Senha-Ficticia-123")
        IdentityProfile.objects.create(user=self.administrator, email_verified_at=timezone.now())
        self.unverified = User.objects.create_user("sem-verificacao", "sem.verificacao@example.invalid", "Senha-Ficticia-123")
        IdentityProfile.objects.create(user=self.unverified)

    def verified_superuser_login(self):
        self.client.force_login(self.superuser)
        device = TOTPDevice.objects.create(user=self.superuser, name="Teste", confirmed=True)
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

    def test_provisioning_names_verified_administrator_and_records_audit(self):
        self.verified_superuser_login()
        response = self.client.post(
            reverse("communities:create"),
            {
                "name": "Comunidade Piloto",
                "slug": "comunidade-piloto",
                "description": "Espaço do Beta fechado.",
                "admin_email": self.administrator.email.upper(),
            },
        )
        self.assertRedirects(response, reverse("communities:detail", args=["comunidade-piloto"]))
        community = Community.objects.get(slug="comunidade-piloto")
        self.assertEqual(community.memberships.filter(role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE).count(), 2)
        self.assertTrue(community.memberships.filter(user=self.administrator).exists())
        self.assertTrue(AuditEvent.objects.filter(action="community.created", target_id=str(community.pk)).exists())

    def test_unverified_administrator_is_rejected_without_creating_community(self):
        self.verified_superuser_login()
        response = self.client.post(
            reverse("communities:create"),
            {
                "name": "Comunidade Inválida",
                "slug": "comunidade-invalida",
                "description": "",
                "admin_email": self.unverified.email,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "precisa verificar o e-mail")
        self.assertFalse(Community.objects.filter(slug="comunidade-invalida").exists())
