import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from audit.services import record_event
from identity.services import email_is_verified

from .models import Community, Event, Invitation, Membership, MembershipRequest


class FlowError(Exception):
    pass


def hash_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_invitation(*, community, email, role, created_by, validity_days=7):
    if role not in {Membership.Role.MEMBER, Membership.Role.GUEST}:
        raise FlowError("Perfil de convite inválido.")
    raw_token = secrets.token_urlsafe(32)
    with transaction.atomic():
        invitation = Invitation.objects.create(
            community=community,
            email=email.strip().lower(),
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
            details={"email_domain": invitation.email.split("@")[-1], "role": role},
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
        if invitation.email.lower() != user.email.lower():
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


def request_membership(*, community, user, message=""):
    if Membership.objects.filter(community=community, user=user, status=Membership.Status.ACTIVE).exists():
        raise FlowError("Você já participa desta comunidade.")
    with transaction.atomic():
        request_obj, _ = MembershipRequest.objects.select_for_update().get_or_create(
            community=community,
            user=user,
            defaults={"message": message},
        )
        request_obj.message = message
        request_obj.status = MembershipRequest.Status.PENDING
        request_obj.reviewed_by = None
        request_obj.reviewed_at = None
        request_obj.review_reason = ""
        request_obj.save()
        record_event(actor=user, action="membership.requested", target=request_obj, community=community)
        return request_obj


def review_membership_request(*, request_obj, reviewer, approve, reason=""):
    with transaction.atomic():
        request_obj = MembershipRequest.objects.select_for_update().select_related("community", "user").get(
            pk=request_obj.pk
        )
        if request_obj.status != MembershipRequest.Status.PENDING:
            raise FlowError("Esta solicitação já foi analisada.")
        request_obj.reviewed_by = reviewer
        request_obj.reviewed_at = timezone.now()
        request_obj.review_reason = reason
        if approve:
            request_obj.status = MembershipRequest.Status.APPROVED
            membership, _ = Membership.objects.select_for_update().get_or_create(
                community=request_obj.community,
                user=request_obj.user,
                defaults={"role": Membership.Role.MEMBER, "status": Membership.Status.PENDING},
            )
            membership.activate(Membership.Role.MEMBER)
            membership.save()
        else:
            request_obj.status = MembershipRequest.Status.DECLINED
            membership, _ = Membership.objects.get_or_create(
                community=request_obj.community,
                user=request_obj.user,
                defaults={"role": Membership.Role.MEMBER, "status": Membership.Status.DECLINED},
            )
            if membership.status == Membership.Status.PENDING:
                membership.status = Membership.Status.DECLINED
                membership.save()
        request_obj.save()
        record_event(
            actor=reviewer,
            action="membership.approved" if approve else "membership.declined",
            target=request_obj,
            community=request_obj.community,
            details={"status": request_obj.status, "reason": reason},
        )
        return request_obj


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
