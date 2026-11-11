from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Community, Event, Membership


class EventViewsTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin-eventos", "admin.eventos@example.invalid", "Senha-Ficticia-123")
        self.member = User.objects.create_user("membro-eventos", "membro.eventos@example.invalid", "Senha-Ficticia-123")
        self.guest = User.objects.create_user("convidado-eventos", "guest.eventos@example.invalid", "Senha-Ficticia-123")
        self.outsider = User.objects.create_user("externo-eventos", "externo.eventos@example.invalid", "Senha-Ficticia-123")
        self.community = Community.objects.create(name="Comunidade Alfa", slug="alfa-eventos", created_by=self.admin)
        self.other = Community.objects.create(name="Comunidade Beta", slug="beta-eventos", created_by=self.admin)
        for user, role in ((self.member, Membership.Role.MEMBER), (self.guest, Membership.Role.GUEST)):
            Membership.objects.create(
                community=self.community,
                user=user,
                role=role,
                status=Membership.Status.ACTIVE,
                joined_at=timezone.now(),
            )
        self.starts_at = timezone.now() + timedelta(days=7)
        self.event = self.create_event()
        self.other_event = self.create_event(
            community=self.other,
            slug="evento-reservado",
            title="Evento Reservado da Beta",
        )

    def create_event(self, community=None, **overrides):
        community = community or self.community
        defaults = {
            "title": "Encontro Fictício",
            "slug": "encontro-ficticio",
            "description": "Uma descrição fictícia para validar a apresentação do evento.",
            "category": "Encontro",
            "location": "Espaço Fictício",
            "starts_at": self.starts_at,
            "ends_at": self.starts_at + timedelta(hours=2),
            "capacity": 80,
            "price": Decimal("0.00"),
            "included_in_membership": True,
            "status": Event.Status.AVAILABLE,
            "created_by": self.admin,
        }
        defaults.update(overrides)
        return Event.objects.create(community=community, **defaults)

    def test_catalog_displays_events_prices_and_all_statuses(self):
        self.create_event(
            slug="ultimas-vagas",
            title="Laboratório de Ideias",
            status=Event.Status.LAST_SEATS,
            included_in_membership=False,
            price=Decimal("45.00"),
        )
        self.create_event(
            slug="esgotado",
            title="Sessão Encerrada",
            status=Event.Status.SOLD_OUT,
            included_in_membership=False,
            price=Decimal("30.00"),
        )
        self.create_event(slug="cancelado", title="Encontro Cancelado", status=Event.Status.CANCELLED)
        self.client.force_login(self.member)
        response = self.client.get(reverse("communities:events", args=[self.community.slug]))
        self.assertEqual(response.status_code, 200)
        for content in (
            "Encontro Fictício",
            "Laboratório de Ideias",
            "Sessão Encerrada",
            "Encontro Cancelado",
            "Evento Reservado da Beta",
            "Disponível",
            "Últimas vagas",
            "Esgotado",
            "Cancelado",
            "45,00",
        ):
            if content == "Evento Reservado da Beta":
                self.assertNotContains(response, content)
            else:
                self.assertContains(response, content)

    def test_detail_shows_membership_benefit_without_commercial_actions(self):
        self.client.force_login(self.member)
        response = self.client.get(
            reverse("communities:event_detail", args=[self.community.slug, self.event.slug])
        )
        self.assertContains(response, "Incluído na assinatura fictícia")
        self.assertContains(response, "Capacidade")
        self.assertNotContains(response, "R$")
        self.assertNotContains(response, "Comprar")
        self.assertNotContains(response, "Reservar")
        self.assertNotContains(response, "Check-in")

    def test_detail_shows_additional_ticket_price(self):
        event = self.create_event(
            slug="ingresso-adicional",
            included_in_membership=False,
            price=Decimal("45.00"),
            status=Event.Status.LAST_SEATS,
        )
        self.client.force_login(self.member)
        response = self.client.get(reverse("communities:event_detail", args=[self.community.slug, event.slug]))
        self.assertContains(response, "Ingresso adicional")
        self.assertContains(response, "R$ 45,00")
        self.assertContains(response, "Nenhuma reserva, cobrança ou emissão de ingresso")

    def test_anonymous_users_are_redirected_to_login(self):
        for url in (
            reverse("communities:events", args=[self.community.slug]),
            reverse("communities:event_detail", args=[self.community.slug, self.event.slug]),
        ):
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('identity:login')}?next={url}")

    def test_members_and_guests_can_view_but_outsiders_cannot(self):
        urls = (
            reverse("communities:events", args=[self.community.slug]),
            reverse("communities:event_detail", args=[self.community.slug, self.event.slug]),
        )
        for user in (self.member, self.guest):
            self.client.force_login(user)
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.outsider)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_event_from_another_community_cannot_be_read_through_local_url(self):
        self.client.force_login(self.member)
        response = self.client.get(
            reverse("communities:event_detail", args=[self.community.slug, self.other_event.slug])
        )
        self.assertEqual(response.status_code, 404)
        other_catalog = self.client.get(reverse("communities:events", args=[self.other.slug]))
        self.assertEqual(other_catalog.status_code, 403)

    def test_overview_previews_upcoming_events_and_excludes_cancelled(self):
        self.create_event(slug="cancelado", title="Não deve aparecer", status=Event.Status.CANCELLED)
        self.client.force_login(self.member)
        response = self.client.get(reverse("communities:detail", args=[self.community.slug]))
        self.assertContains(response, "Próximos eventos")
        self.assertContains(response, self.event.title)
        self.assertNotContains(response, "Não deve aparecer")
        self.assertContains(response, reverse("communities:events", args=[self.community.slug]))

    def test_demo_seed_is_idempotent_and_keeps_five_events(self):
        output = StringIO()
        call_command("seed_demo", stdout=output)
        call_command("seed_demo", stdout=output)
        community = Community.objects.get(slug="comunidade-ficticia")
        self.assertEqual(community.events.count(), 5)
        self.assertEqual(community.events.values("slug").distinct().count(), 5)
        self.assertIn("5 eventos", output.getvalue())
