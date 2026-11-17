import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from audit.services import record_event
from identity.services import email_is_verified

from .models import Comment, Community, Event, Invitation, Membership, Post, PostImage


class FlowError(Exception):
    pass


MEMBER_INVITE_QUOTA = 2


def hash_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_invitation_by_token(raw_token):
    """Retorna o convite pelo token em texto claro, ou None se não existir."""
    if not raw_token:
        return None
    return Invitation.objects.select_related("community").filter(token_hash=hash_token(raw_token)).first()


def is_active_admin(user, community):
    return Membership.objects.filter(
        community=community,
        user=user,
        status=Membership.Status.ACTIVE,
        role=Membership.Role.ADMIN,
    ).exists()


def invites_used(community, user):
    """Convites do membro que já foram aceitos ou ainda estão pendentes (valem na cota)."""
    return Invitation.objects.filter(
        community=community,
        created_by=user,
        revoked_at__isnull=True,
    ).filter(
        models.Q(accepted_at__isnull=False)
        | models.Q(accepted_at__isnull=True, expired_at__isnull=True, expires_at__gt=timezone.now())
    ).count()


def invite_quota(community, user):
    """Cota de convites restante. Admin ativo tem convites ilimitados (retorna None)."""
    if is_active_admin(user, community):
        return None
    membership = get_active_membership_cached(user, community)
    if membership is None:
        return 0
    total = MEMBER_INVITE_QUOTA + membership.extra_invites
    return max(total - invites_used(community, user), 0)


def get_active_membership_cached(user, community):
    return Membership.objects.filter(
        community=community,
        user=user,
        status=Membership.Status.ACTIVE,
    ).first()


def create_invitation(*, community, email, role, created_by, validity_days=7):
    if role not in {Membership.Role.MEMBER, Membership.Role.GUEST}:
        raise FlowError("Perfil de convite inválido.")
    if not is_active_admin(created_by, community):
        quota = invite_quota(community, created_by)
        if quota is not None and quota <= 0:
            raise FlowError("Você já usou todos os seus convites. Peça ao administrador para liberar mais.")
    raw_token = secrets.token_urlsafe(32)
    with transaction.atomic():
        invitation = Invitation.objects.create(
            community=community,
            email=(email or "").strip().lower(),
            role=role,
            token_hash=hash_token(raw_token),
            expires_at=timezone.now() + timedelta(days=validity_days),
            created_by=created_by,
        )
        record_event(
            actor=created_by,
            action="invitation.created",
            target=invitation,
            community=community,
            details={"email_domain": invitation.email.split("@")[-1] if invitation.email else "", "role": role},
        )
    return invitation, raw_token


def accept_invitation(*, raw_token, user):
    with transaction.atomic():
        invitation = (
            Invitation.objects.select_for_update()
            .select_related("community")
            .filter(token_hash=hash_token(raw_token))
            .first()
        )
        if not invitation:
            raise FlowError("Convite não encontrado.")
        if invitation.revoked_at or invitation.accepted_at or invitation.expired_at or invitation.expires_at <= timezone.now():
            raise FlowError("Este convite não está mais disponível.")
        if invitation.email and invitation.email.lower() != user.email.lower():
            raise FlowError("Entre com a conta que usa o e-mail convidado.")

        membership, _ = Membership.objects.select_for_update().get_or_create(
            community=invitation.community,
            user=user,
            defaults={"role": invitation.role, "status": Membership.Status.PENDING},
        )
        membership.activate(invitation.role)
        membership.save()
        invitation.accepted_at = timezone.now()
        invitation.accepted_by = user
        invitation.save(update_fields=["accepted_at", "accepted_by", "updated_at"])
        record_event(
            actor=user,
            action="invitation.accepted",
            target=invitation,
            community=invitation.community,
            details={"role": membership.role, "status": membership.status},
        )
        return membership


def _protect_last_admin(membership):
    if membership.role != Membership.Role.ADMIN or membership.status != Membership.Status.ACTIVE:
        return
    active_admins = Membership.objects.filter(
        community=membership.community,
        role=Membership.Role.ADMIN,
        status=Membership.Status.ACTIVE,
    ).count()
    if active_admins <= 1:
        raise FlowError("A comunidade precisa manter pelo menos um administrador ativo.")


def change_membership_status(*, membership, actor, new_status):
    if new_status not in {Membership.Status.ACTIVE, Membership.Status.SUSPENDED, Membership.Status.REMOVED}:
        raise FlowError("Situação inválida.")
    if membership.user == actor and new_status != Membership.Status.ACTIVE:
        raise FlowError("Você não pode suspender ou remover a própria conta.")
    with transaction.atomic():
        membership = Membership.objects.select_for_update().select_related("community", "user").get(pk=membership.pk)
        Community.objects.select_for_update().get(pk=membership.community_id)
        _protect_last_admin(membership)
        previous_status = membership.status
        membership.status = new_status
        if new_status == Membership.Status.ACTIVE:
            membership.joined_at = membership.joined_at or timezone.now()
        membership.save()
        record_event(
            actor=actor,
            action=f"membership.{new_status}",
            target=membership,
            community=membership.community,
            details={"previous_status": previous_status, "status": new_status, "role": membership.role},
        )
        return membership


def provision_community(*, creator, data):
    if not creator.is_superuser:
        raise FlowError("Somente o responsável pela plataforma pode provisionar comunidades.")
    email = data["admin_email"].strip().lower()
    administrator = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
    if not administrator or not email_is_verified(administrator):
        raise FlowError("O administrador precisa ter uma conta ativa e o e-mail verificado.")
    slug = slugify(data["slug"])
    if not slug:
        raise FlowError("Informe um identificador válido.")
    if Community.objects.filter(slug=slug).exists():
        raise FlowError("Este identificador já está em uso.")
    with transaction.atomic():
        community = Community.objects.create(
            name=data["name"].strip(),
            slug=slug,
            description=data.get("description", "").strip(),
            created_by=creator,
        )
        for user in {creator, administrator}:
            Membership.objects.create(
                community=community,
                user=user,
                role=Membership.Role.ADMIN,
                status=Membership.Status.ACTIVE,
                joined_at=timezone.now(),
            )
        record_event(
            actor=creator,
            action="community.created",
            target=community,
            community=community,
            details={"title": community.name, "role": Membership.Role.ADMIN},
        )
    return community


def _next_event_slug(community, title):
    base = slugify(title)[:180] or "evento"
    candidate = base
    suffix = 2
    while Event.objects.filter(community=community, slug=candidate).exists():
        candidate = f"{base[:200 - len(str(suffix)) - 1]}-{suffix}"
        suffix += 1
    return candidate


def create_event(*, community, actor, data):
    with transaction.atomic():
        event = Event(
            community=community,
            created_by=actor,
            slug=_next_event_slug(community, data["title"]),
            **data,
        )
        event.full_clean()
        event.save()
        record_event(
            actor=actor,
            action="event.created",
            target=event,
            community=community,
            details={"title": event.title, "status": event.status},
        )
    return event


def update_event(*, event, actor, data):
    with transaction.atomic():
        event = Event.objects.select_for_update().get(pk=event.pk, community=event.community)
        for field, value in data.items():
            setattr(event, field, value)
        event.full_clean()
        event.save()
        record_event(
            actor=actor,
            action="event.updated",
            target=event,
            community=event.community,
            details={"title": event.title, "status": event.status},
        )
    return event


def cancel_event(*, event, actor):
    with transaction.atomic():
        event = Event.objects.select_for_update().get(pk=event.pk, community=event.community)
        if event.status == Event.Status.CANCELLED:
            raise FlowError("Este evento já está cancelado.")
        event.status = Event.Status.CANCELLED
        event.is_featured = False
        event.save(update_fields=["status", "is_featured", "updated_at"])
        record_event(
            actor=actor,
            action="event.cancelled",
            target=event,
            community=event.community,
            details={"title": event.title, "status": event.status},
        )
    return event


def change_membership_role(*, membership, actor, new_role):
    if new_role not in Membership.Role.values:
        raise FlowError("Perfil inválido.")
    if membership.user == actor and new_role != Membership.Role.ADMIN:
        raise FlowError("Você não pode rebaixar o próprio perfil.")
    with transaction.atomic():
        membership = Membership.objects.select_for_update().select_related("community", "user").get(pk=membership.pk)
        Community.objects.select_for_update().get(pk=membership.community_id)
        _protect_last_admin(membership)
        membership.role = new_role
        membership.save()
        record_event(
            actor=actor,
            action="membership.role_changed",
            target=membership,
            community=membership.community,
            details={"role": new_role, "status": membership.status},
        )
        return membership


def grant_extra_invites(*, membership, actor, amount=1):
    if not is_active_admin(actor, membership.community):
        raise FlowError("Somente o administrador pode liberar convites extras.")
    if membership.status != Membership.Status.ACTIVE:
        raise FlowError("Só é possível liberar convites para vínculos ativos.")
    if amount < 1 or amount > 50:
        raise FlowError("Quantidade inválida.")
    with transaction.atomic():
        membership = Membership.objects.select_for_update().select_related("community", "user").get(pk=membership.pk)
        previous = membership.extra_invites
        membership.extra_invites = previous + amount
        membership.save(update_fields=["extra_invites", "updated_at"])
        record_event(
            actor=actor,
            action="membership.extra_invites_granted",
            target=membership,
            community=membership.community,
            details={"user": membership.user.username, "previous": previous, "added": amount, "total": membership.extra_invites},
        )
        return membership


def create_post(*, community, author, body, image=None):
    membership = get_active_membership_cached(author, community)
    if membership is None:
        raise FlowError("Apenas membros ativos podem publicar no mural.")
    text = (body or "").strip()
    if not text:
        raise FlowError("Escreva algo para publicar.")
    raw = content_type = None
    if image is not None:
        raw = image.read()
        if not raw:
            raise FlowError("O arquivo de imagem está vazio.")
        if len(raw) > PostImage.MAX_BYTES:
            raise FlowError("A imagem ultrapassa 2 MB. Envie um arquivo menor.")
        content_type = PostImage.sniff_content_type(raw[:16])
        if content_type is None:
            raise FlowError("Formato não suportado. Envie PNG, JPEG ou WebP.")
    with transaction.atomic():
        post = Post.objects.create(community=community, author=author, body=text[:2000])
        if raw is not None:
            PostImage.objects.create(post=post, data=raw, content_type=content_type, size=len(raw))
        record_event(
            actor=author,
            action="post.created",
            target=post,
            community=community,
            details={"length": len(text), "with_image": raw is not None},
        )
    return post


def add_comment(*, post, author, body):
    membership = get_active_membership_cached(author, post.community)
    if membership is None:
        raise FlowError("Apenas membros ativos podem comentar.")
    text = (body or "").strip()
    if not text:
        raise FlowError("Escreva algo para comentar.")
    return Comment.objects.create(post=post, author=author, body=text[:800])


def toggle_like(*, post, user):
    membership = get_active_membership_cached(user, post.community)
    if membership is None:
        raise FlowError("Apenas membros ativos podem curtir.")
    if post.likes.filter(pk=user.pk).exists():
        post.likes.remove(user)
        return False
    post.likes.add(user)
    return True


def delete_post(*, post, actor):
    membership = get_active_membership_cached(actor, post.community)
    is_moderator = bool(membership and membership.role in {Membership.Role.ADMIN, Membership.Role.MODERATOR})
    if post.author_id != actor.pk and not is_moderator:
        raise FlowError("Somente o autor ou um moderador pode remover a publicação.")
    community = post.community
    record_event(
        actor=actor,
        action="post.removed",
        target=post,
        community=community,
        details={"author": post.author.username, "reason": "moderacao" if is_moderator else "proprio_autor"},
    )
    post.delete()
