"""Cria 3 contas de administrador na homologacao TUDUN (login + senha).

Gera senhas fortes, cria o usuario, membership ADMIN ativo, e-mail verificado.
Revoga convites pendentes deixados para tras. Imprime apenas login e senha.
"""
import secrets
import string

from django.contrib.auth import get_user_model
from django.utils import timezone

from audit.services import record_event
from communities.models import Community, Invitation, Membership
from identity.models import IdentityProfile

User = get_user_model()
mateus = User.objects.get(username="mateus")
community = Community.objects.get(slug="tudun")

# Revoga convites pendentes (abordagem por link nao sera usada para admins)
revogados = 0
pendentes = Invitation.objects.filter(
    community=community,
    accepted_at__isnull=True,
    revoked_at__isnull=True,
    expires_at__gt=timezone.now(),
)
for inv in pendentes:
    inv.revoked_at = timezone.now()
    inv.save(update_fields=["revoked_at", "updated_at"])
    revogados += 1
print(f"convites revogados: {revogados}")

alfabeto = string.ascii_letters + string.digits
credenciais = []
for i in range(2, 5):
    username = f"admin{i}"
    senha = "".join(secrets.choice(alfabeto) for _ in range(14))
    if User.objects.filter(username=username).exists():
        print(f"{username}: ja existe, pulando")
        continue
    email = f"{username}@tudun.local"
    user = User.objects.create_user(username=username, email=email, password=senha, is_active=True)
    IdentityProfile.objects.create(user=user, email_verified_at=timezone.now())
    Membership.objects.create(
        community=community,
        user=user,
        role=Membership.Role.ADMIN,
        status=Membership.Status.ACTIVE,
        joined_at=timezone.now(),
    )
    record_event(
        actor=mateus,
        action="membership.role_changed",
        target=user,
        community=community,
        details={"username": username, "role": Membership.Role.ADMIN, "via": "provisionamento_direto"},
    )
    credenciais.append((username, senha))

print("contas criadas:")
for username, senha in credenciais:
    print(f"  login: {username}")
    print(f"  senha: {senha}")
