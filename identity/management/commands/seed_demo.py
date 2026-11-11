from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from communities.models import Community, Event, Membership, Notice
from identity.models import IdentityProfile


class Command(BaseCommand):
    help = "Cria apenas dados fictícios para validação local da Etapa 1."

    def handle(self, *args, **options):
        User = get_user_model()
        admin, created = User.objects.get_or_create(
            username="admin_teste",
            defaults={"email": "admin.teste@example.invalid", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("TudunTeste-2026!")
            admin.save()
        member, created = User.objects.get_or_create(
            username="membro_teste", defaults={"email": "membro.teste@example.invalid"}
        )
        if created:
            member.set_password("TudunTeste-2026!")
            member.save()
        for user in (admin, member):
            IdentityProfile.objects.get_or_create(
                user=user,
                defaults={"email_verified_at": timezone.now() if user.email else None},
            )
        community, created = Community.objects.get_or_create(
            slug="comunidade-ficticia",
            defaults={
                "name": "Comunidade Fictícia",
                "description": "Espaço de desenvolvimento para validar acessos, convites e avisos.",
                "created_by": admin,
            },
        )
        Membership.objects.get_or_create(
            community=community,
            user=admin,
            defaults={"role": Membership.Role.ADMIN, "status": Membership.Status.ACTIVE, "joined_at": timezone.now()},
        )
        Membership.objects.get_or_create(
            community=community,
            user=member,
            defaults={"role": Membership.Role.MEMBER, "status": Membership.Status.ACTIVE, "joined_at": timezone.now()},
        )
        Notice.objects.update_or_create(
            community=community,
            title="Bem-vindo ao ambiente de teste",
            defaults={
                "author": admin,
                "body": (
                    "Todos os dados desta comunidade são fictícios. Os eventos podem ser explorados no catálogo; "
                    "reservas, pagamentos e check-in não estão habilitados."
                ),
                "is_active": True,
            },
        )

        base_start = timezone.localtime().replace(hour=19, minute=0, second=0, microsecond=0)
        event_fixtures = [
            {
                "slug": "encontro-da-comunidade",
                "days": 7,
                "title": "Encontro da Comunidade",
                "description": (
                    "Uma noite para aproximar participantes, apresentar novos projetos e criar conexões "
                    "em uma programação acolhedora com conversas mediadas."
                ),
                "category": "Encontro",
                "location": "Casa TUDUN · Espaço Central",
                "capacity": 120,
                "price": Decimal("0.00"),
                "included_in_membership": True,
                "status": Event.Status.AVAILABLE,
                "is_featured": True,
            },
            {
                "slug": "laboratorio-de-ideias",
                "days": 14,
                "title": "Laboratório de Ideias",
                "description": (
                    "Uma experiência prática em pequenos grupos para transformar repertório em projetos. "
                    "Os participantes percorrem exercícios de ideação, protótipo e apresentação."
                ),
                "category": "Workshop",
                "location": "Ateliê Norte · Sala 2",
                "capacity": 24,
                "price": Decimal("45.00"),
                "included_in_membership": False,
                "status": Event.Status.LAST_SEATS,
                "is_featured": False,
            },
            {
                "slug": "noite-de-historias",
                "days": 21,
                "title": "Noite de Histórias",
                "description": (
                    "Narrativas ao vivo, música e memórias compartilhadas em um encontro intimista. "
                    "A assinatura fictícia inclui acesso a esta programação especial."
                ),
                "category": "Cultura",
                "location": "Teatro Estúdio · Palco Principal",
                "capacity": 80,
                "price": Decimal("0.00"),
                "included_in_membership": True,
                "status": Event.Status.AVAILABLE,
                "is_featured": False,
            },
            {
                "slug": "sessao-encerrada",
                "days": 28,
                "title": "Sessão Encerrada",
                "description": (
                    "Uma sessão fictícia de cinema e conversa com convidados, apresentada no catálogo "
                    "para demonstrar o estado de lotação esgotada."
                ),
                "category": "Cinema",
                "location": "Cine Clube · Sala Verde",
                "capacity": 60,
                "price": Decimal("30.00"),
                "included_in_membership": False,
                "status": Event.Status.SOLD_OUT,
                "is_featured": False,
            },
            {
                "slug": "encontro-cancelado",
                "days": 35,
                "title": "Encontro Cancelado",
                "description": (
                    "Este registro fictício demonstra como uma programação cancelada permanece identificada "
                    "com clareza, sem induzir o participante a uma ação comercial."
                ),
                "category": "Encontro",
                "location": "Casa TUDUN · Jardim",
                "capacity": 50,
                "price": Decimal("0.00"),
                "included_in_membership": True,
                "status": Event.Status.CANCELLED,
                "is_featured": False,
            },
        ]
        for fixture in event_fixtures:
            days = fixture.pop("days")
            starts_at = base_start + timedelta(days=days)
            Event.objects.update_or_create(
                community=community,
                slug=fixture.pop("slug"),
                defaults={
                    **fixture,
                    "starts_at": starts_at,
                    "ends_at": starts_at + timedelta(hours=2),
                    "created_by": admin,
                },
            )

        self.stdout.write(self.style.SUCCESS(f"Dados fictícios prontos: {len(event_fixtures)} eventos na agenda."))
        self.stdout.write("Contas: admin_teste e membro_teste")
        self.stdout.write("Senha local de desenvolvimento: TudunTeste-2026!")
        self.stdout.write("Ao entrar como admin_teste, configure um MFA próprio de teste.")
