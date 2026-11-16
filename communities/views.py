from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditEvent
from audit.services import record_event
from identity.ratelimit import rate_limit
from identity.services import email_is_verified

from .forms import (
    CommunityForm,
    EventForm,
    InvitationForm,
    MembershipRoleForm,
    NoticeForm,
)
from .models import Community, Event, Invitation, Membership, Notice
from .permissions import get_active_membership, is_community_admin, require_permission
from .services import (
    FlowError,
    accept_invitation,
    cancel_event,
    change_membership_role,
    change_membership_status,
    create_event,
    create_invitation,
    grant_extra_invites,
    invite_quota,
    provision_community,
    update_event,
)


def home(request):
    memberships = []
    verified = False
    if request.user.is_authenticated:
        verified = email_is_verified(request.user)
        memberships = (
            Membership.objects.filter(user=request.user, status=Membership.Status.ACTIVE)
            .select_related("community")
            .order_by("community__name")
        )
    return render(request, "communities/home.html", {"memberships": memberships, "email_verified": verified})


@login_required
@user_passes_test(lambda user: user.is_superuser)
def community_create(request):
    form = CommunityForm(request.POST or None, creator=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            community = provision_community(creator=request.user, data=form.cleaned_data)
        except FlowError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Comunidade privada criada e administrador nomeado.")
            return redirect("communities:detail", slug=community.slug)
    return render(request, "communities/community_form.html", {"form": form})


@login_required
def community_detail(request, slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "view")
    membership = get_active_membership(request.user, community)
    return render(
        request,
        "communities/detail.html",
        {
            "community": community,
            "membership": membership,
            "notices": community.notices.filter(is_active=True),
            "upcoming_events": community.events.filter(starts_at__gte=timezone.now())
            .exclude(status=Event.Status.CANCELLED)[:3],
            "can_manage": membership.role == Membership.Role.ADMIN,
            "can_moderate": membership.role in {Membership.Role.ADMIN, Membership.Role.MODERATOR},
        },
    )


@login_required
def event_list(request, slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "view")
    membership = get_active_membership(request.user, community)
    return render(
        request,
        "communities/events.html",
        {
            "community": community,
            "membership": membership,
            "can_moderate": membership.role in {Membership.Role.ADMIN, Membership.Role.MODERATOR},
            "events": community.events.all(),
        },
    )


@login_required
def event_detail(request, slug, event_slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "view")
    event = get_object_or_404(Event, community=community, slug=event_slug)
    membership = get_active_membership(request.user, community)
    return render(
        request,
        "communities/event_detail.html",
        {
            "community": community,
            "membership": membership,
            "can_moderate": membership.role in {Membership.Role.ADMIN, Membership.Role.MODERATOR},
            "event": event,
        },
    )


@login_required
@rate_limit(rate="20/m", key="user_or_ip")
def event_create(request, slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "events")
    form = EventForm(request.POST or None, community=community)
    if request.method == "POST" and form.is_valid():
        event = create_event(community=community, actor=request.user, data=form.cleaned_data)
        messages.success(request, "Evento criado e publicado na agenda.")
        return redirect("communities:event_detail", slug=slug, event_slug=event.slug)
    return render(
        request,
        "communities/event_form.html",
        {"community": community, "form": form, "is_edit": False},
    )


@login_required
@rate_limit(rate="20/m", key="user_or_ip")
def event_update(request, slug, event_slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "events")
    event = get_object_or_404(Event, community=community, slug=event_slug)
    form = EventForm(request.POST or None, instance=event, community=community)
    if request.method == "POST" and form.is_valid():
        update_event(event=event, actor=request.user, data=form.cleaned_data)
        messages.success(request, "Evento atualizado.")
        return redirect("communities:event_detail", slug=slug, event_slug=event.slug)
    return render(
        request,
        "communities/event_form.html",
        {"community": community, "event": event, "form": form, "is_edit": True},
    )


@login_required
@rate_limit(rate="10/m", key="user_or_ip")
def event_cancel(request, slug, event_slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "events")
    event = get_object_or_404(Event, community=community, slug=event_slug)
    if request.method == "POST":
        try:
            cancel_event(event=event, actor=request.user)
        except FlowError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Evento cancelado. O registro permanece na agenda para consulta.")
        return redirect("communities:event_detail", slug=slug, event_slug=event.slug)
    return render(
        request,
        "communities/confirm.html",
        {"community": community, "object": event, "action_label": "Cancelar evento"},
    )


def invitation_accept(request, token):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('identity:signup')}?convite={token}")
    if request.method == "POST":
        try:
            membership = accept_invitation(raw_token=token, user=request.user)
        except FlowError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Convite aceito. Seu acesso está ativo.")
            return redirect("communities:detail", slug=membership.community.slug)
    return render(request, "communities/invitation_accept.html")


@login_required
def members(request, slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "members")
    return render(
        request,
        "communities/members.html",
        {"community": community, "memberships": community.memberships.select_related("user")},
    )


@login_required
@rate_limit(rate="10/m", key="user_or_ip")
def invitations(request, slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "view")
    membership = get_active_membership(request.user, community)
    quota = invite_quota(community, request.user)
    form = InvitationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            invitation, raw_token = create_invitation(
                community=community,
                email=form.cleaned_data["email"],
                role=form.cleaned_data["role"],
                created_by=request.user,
            )
        except FlowError as exc:
            form.add_error(None, str(exc))
        else:
            accept_url = request.build_absolute_uri(reverse("communities:accept_invitation", kwargs={"token": raw_token}))
            request.session["last_invite_link"] = accept_url
            if invitation.email:
                try:
                    send_mail(
                        subject=f"Você foi convidado(a) para {community.name}",
                        message=(
                            f"Você recebeu um convite para participar da comunidade {community.name}.\n\n"
                            f"Acesse: {accept_url}\n\n"
                            f"O convite expira em {invitation.expires_at:%d/%m/%Y %H:%M}."
                        ),
                        from_email=None,
                        recipient_list=[invitation.email],
                    )
                except Exception:
                    messages.warning(request, "Convite criado, mas o envio do e-mail falou. Copie o link abaixo e envie por sua conta.")
                else:
                    messages.success(request, "Convite criado e e-mail enviado.")
            else:
                messages.success(request, "Convite criado. Copie o link abaixo e envie para a pessoa.")
            return redirect("communities:invitations", slug=slug)
    my_invitations = community.invitations.filter(created_by=request.user)
    last_link = request.session.pop("last_invite_link", None)
    return render(
        request,
        "communities/invitations.html",
        {
            "community": community,
            "membership": membership,
            "form": form,
            "quota": quota,
            "last_link": last_link,
            "invitations": my_invitations,
        },
    )


@login_required
@rate_limit(rate="10/m", key="user_or_ip")
def membership_extra_invites(request, slug, pk):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "admin")
    membership = get_object_or_404(Membership, pk=pk, community=community)
    if request.method == "POST":
        try:
            amount = int(request.POST.get("amount", "1"))
        except ValueError:
            amount = 0
        try:
            grant_extra_invites(membership=membership, actor=request.user, amount=amount)
        except FlowError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Convite extra liberado para {membership.user.username}.")
    return redirect("communities:members", slug=slug)


@login_required
def invitation_revoke(request, slug, pk):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "view")
    invitation = get_object_or_404(Invitation, pk=pk, community=community)
    if invitation.created_by != request.user and not is_community_admin(request.user, community):
        raise PermissionDenied("Você só pode revogar os seus próprios convites.")
    if request.method == "POST":
        if invitation.accepted_at or invitation.revoked_at or invitation.expired_at:
            messages.error(request, "Este convite não pode ser revogado.")
        else:
            invitation.revoked_at = timezone.now()
            invitation.save(update_fields=["revoked_at", "updated_at"])
            record_event(actor=request.user, action="invitation.revoked", target=invitation, community=community)
            messages.success(request, "Convite revogado.")
        return redirect("communities:invitations", slug=slug)
    return render(request, "communities/confirm.html", {"community": community, "object": invitation, "action_label": "Revogar convite"})


@login_required
def membership_status(request, slug, pk, new_status):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "admin")
    membership = get_object_or_404(Membership, pk=pk, community=community)
    labels = {Membership.Status.SUSPENDED: "Suspender acesso", Membership.Status.REMOVED: "Remover acesso", Membership.Status.ACTIVE: "Reativar acesso"}
    if new_status not in labels:
        messages.error(request, "Ação inválida.")
        return redirect("communities:members", slug=slug)
    if request.method == "POST":
        try:
            change_membership_status(membership=membership, actor=request.user, new_status=new_status)
        except FlowError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Situação do vínculo atualizada.")
        return redirect("communities:members", slug=slug)
    return render(request, "communities/confirm.html", {"community": community, "object": membership, "action_label": labels[new_status]})


@login_required
def membership_role(request, slug, pk):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "admin")
    membership = get_object_or_404(Membership, pk=pk, community=community)
    form = MembershipRoleForm(request.POST or None, initial={"role": membership.role})
    if request.method == "POST" and form.is_valid():
        try:
            change_membership_role(membership=membership, actor=request.user, new_role=form.cleaned_data["role"])
        except FlowError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Perfil atualizado.")
            return redirect("communities:members", slug=slug)
    return render(request, "communities/role_form.html", {"community": community, "membership": membership, "form": form})


@login_required
def notice_create(request, slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "publish")
    form = NoticeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        notice = form.save(commit=False)
        notice.community = community
        notice.author = request.user
        notice.save()
        record_event(actor=request.user, action="notice.published", target=notice, community=community, details={"title": notice.title})
        messages.success(request, "Aviso publicado.")
        return redirect("communities:detail", slug=slug)
    return render(request, "communities/notice_form.html", {"community": community, "form": form})


@login_required
def notice_remove(request, slug, pk):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "publish")
    notice = get_object_or_404(Notice, pk=pk, community=community)
    if request.method == "POST":
        notice.is_active = False
        notice.save(update_fields=["is_active", "updated_at"])
        record_event(actor=request.user, action="notice.removed", target=notice, community=community, details={"title": notice.title})
        messages.success(request, "Aviso retirado.")
        return redirect("communities:detail", slug=slug)
    return render(request, "communities/confirm.html", {"community": community, "object": notice, "action_label": "Retirar aviso"})


@login_required
def audit_list(request, slug):
    community = get_object_or_404(Community, slug=slug)
    require_permission(request.user, community, "admin")
    return render(
        request,
        "communities/audit.html",
        {"community": community, "events": AuditEvent.objects.filter(community=community).select_related("actor")[:200]},
    )
