"""Provisiona a comunidade real TUDUN na homologacao e verifica o e-mail do admin.

Roda com DATABASE_URL de homologacao. Imprime apenas informacoes nao sensiveis.
"""
from django.contrib.auth import get_user_model
from django.utils import timezone

from communities.models import Community, Membership, Notice
from communities.services import provision_community
from identity.models import IdentityProfile

User = get_user_model()
mateus = User.objects.get(username="mateus")

profile, _ = IdentityProfile.objects.get_or_create(user=mateus)
if profile.email_verified_at is None:
    profile.email_verified_at = timezone.now()
    profile.save(update_fields=["email_verified_at", "updated_at"])
    print("e-mail do mateus marcado como verificado")
else:
    print("e-mail do mateus ja estava verificado")

if Community.objects.filter(slug="tudun").exists():
    print("comunidade 'tudun' ja existe; nada a fazer")
else:
    community = provision_community(
        creator=mateus,
        data={
            "name": "TUDUN",
            "slug": "tudun",
            "description": "Comunidade fechada do TUDUN. A entrada é somente por convite de um membro.",
            "admin_email": mateus.email,
        },
    )
    Notice.objects.create(
        community=community,
        author=mateus,
        title="Bem-vindo à TUDUN",
        body="Esta é a comunidade fechada da TUDUN. Membros convidam pessoas de confiança pelo link de convite, e cada membro pode trazer duas pessoas.",
    )
    print("comunidade criada:", community.name, "| slug:", community.slug)
    print("membros admin:", Membership.objects.filter(community=community, role="ADMIN").count())
