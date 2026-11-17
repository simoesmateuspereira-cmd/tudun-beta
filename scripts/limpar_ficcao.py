"""Limpa dados ficticios da homologacao TUDUN apos o fechamento da comunidade.

- Remove as contas ficticias admin_teste e membro_teste (e seus vínculos).
- Renomeia a "Comunidade Fictícia" para o nome real e limpa avisos de teste.
- Zera convites extras (garantia) e registra o evento na auditoria.

Uso: python manage.py shell < scripts/limpar_ficcao.py  (com DATABASE_URL de homologacao)
"""
from django.contrib.auth import get_user_model
from django.utils import timezone

from audit.services import record_event
from communities.models import Community, Invitation, Membership, Notice

User = get_user_model()

report = []

for username in ("admin_teste", "membro_teste"):
    user = User.objects.filter(username=username).first()
    if user:
        memberships = list(Membership.objects.filter(user=user).select_related("community"))
        communities = [m.community for m in memberships]
        Invitation.objects.filter(created_by=user).delete()
        user.delete()  # em cascata: memberships, perfil, convites aceitos
        report.append(f"conta removida: {username} ({len(communities)} vínculo(s))")
    else:
        report.append(f"conta ausente: {username}")

community = Community.objects.filter(slug="comunidade-ficticia").first()
if community:
    deleted_notices, _ = Notice.objects.filter(community=community, title="Bem-vindo ao ambiente de teste").delete()
    community.name = "TUDUN"
    community.description = "Comunidade fechada do TUDUN. A entrada é somente por convite de um membro."
    community.save(update_fields=["name", "description", "updated_at"])
    report.append(f"comunidade renomeada para TUDUN; {deleted_notices} aviso(s) de teste removido(s)")
else:
    report.append("comunidade comunidade-ficticia nao encontrada (talvez ja renomeada)")

admins = Membership.objects.filter(community=community, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE) if community else []
if admins.exists():
    actor = admins.first().user
    record_event(
        actor=actor,
        action="community.fictional_data_cleaned",
        target=community,
        community=community,
        details={"cleaned_at": timezone.now().isoformat()},
    )

print("LIMPEZA CONCLUIDA:")
for line in report:
    print(" -", line)
