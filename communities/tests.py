from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from audit.models import AuditEvent
from audit.services import record_event

from .models import Community, Invitation, Membership, Notice
from .services import (
    FlowError,
    accept_invitation,
    change_membership_role,
    change_membership_status,
    create_invitation,
    grant_extra_invites,
    invite_quota,
)


class CommunityTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin", "admin@example.invalid", "Senha-Ficticia-123")
        self.moderator = User.objects.create_user("moderador", "mod@example.invalid", "Senha-Ficticia-123")
        self.member = User.objects.create_user("membro", "membro@example.invalid", "Senha-Ficticia-123")
        self.guest = User.objects.create_user("convidado", "guest@example.invalid", "Senha-Ficticia-123")
        self.outsider = User.objects.create_user("externo", "externo@example.invalid", "Senha-Ficticia-123")
        self.community = Community.objects.create(name="Alfa Fictícia", slug="alfa", created_by=self.admin)
        self.other = Community.objects.create(name="Beta Fictícia", slug="beta", created_by=self.admin)
        self.admin_membership = self.join(self.admin, Membership.Role.ADMIN)
        self.join(self.moderator, Membership.Role.MODERATOR)
        self.join(self.member, Membership.Role.MEMBER)
        self.join(self.guest, Membership.Role.GUEST)
        Membership.objects.create(
            community=self.other, user=self.admin, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE
        )

    def join(self, user, role=Membership.Role.MEMBER, community=None, status=Membership.Status.ACTIVE):
        return Membership.objects.create(
            community=community or self.community, user=user, role=role, status=status, joined_at=timezone.now()
        )

    def verified_login(self, user):
        self.client.force_login(user)
        device = TOTPDevice.objects.create(user=user, name="Teste", confirmed=True)
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

    def test_uses_real_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")

    def test_member_quota_is_two_invites_and_counts_pending_and_accepted(self):
        self.assertEqual(invite_quota(self.community, self.member), 2)
        create_invitation(community=self.community, email="", role=Membership.Role.MEMBER, created_by=self.member)
        self.assertEqual(invite_quota(self.community, self.member), 1)
        _, raw = create_invitation(community=self.community, email="", role=Membership.Role.MEMBER, created_by=self.member)
        self.assertEqual(invite_quota(self.community, self.member), 0)
        accept_invitation(raw_token=raw, user=self.outsider)
        self.assertEqual(invite_quota(self.community, self.member), 0)
        with self.assertRaisesMessage(FlowError, "usou todos"):
            create_invitation(community=self.community, email="", role=Membership.Role.MEMBER, created_by=self.member)

    def test_admin_has_unlimited_invites(self):
        self.assertIsNone(invite_quota(self.community, self.admin))
        for _ in range(4):
            create_invitation(community=self.community, email="", role=Membership.Role.MEMBER, created_by=self.admin)

    def test_admin_grant_extra_invites_restores_member_quota(self):
        for _ in range(2):
            create_invitation(community=self.community, email="", role=Membership.Role.MEMBER, created_by=self.member)
        membership = Membership.objects.get(community=self.community, user=self.member)
        grant_extra_invites(membership=membership, actor=self.admin, amount=1)
        membership.refresh_from_db()
        self.assertEqual(membership.extra_invites, 1)
        self.assertEqual(invite_quota(self.community, self.member), 1)

    def test_non_admin_cannot_grant_extra_invites(self):
        membership = Membership.objects.get(community=self.community, user=self.member)
        with self.assertRaisesMessage(FlowError, "administrador"):
            grant_extra_invites(membership=membership, actor=self.moderator, amount=1)

    def test_invitation_without_email_accepts_any_user(self):
        _, raw = create_invitation(community=self.community, email="", role=Membership.Role.MEMBER, created_by=self.admin)
        membership = accept_invitation(raw_token=raw, user=self.outsider)
        self.assertEqual(membership.status, Membership.Status.ACTIVE)

    def test_expired_invite_does_not_consume_quota(self):
        invitation, _ = create_invitation(community=self.community, email="", role=Membership.Role.MEMBER, created_by=self.member)
        Invitation.objects.filter(pk=invitation.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1), expired_at=timezone.now()
        )
        self.assertEqual(invite_quota(self.community, self.member), 2)

    def test_private_communities_are_isolated(self):
        self.client.force_login(self.member)
        allowed = self.client.get(reverse("communities:detail", args=[self.community.slug]))
        denied = self.client.get(reverse("communities:detail", args=[self.other.slug]))
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(denied.status_code, 403)
        self.assertNotContains(allowed, self.other.name)

    def test_member_and_guest_can_invite_but_not_manage(self):
        for user in (self.member, self.guest):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("communities:detail", args=["alfa"])).status_code, 200)
            self.assertEqual(self.client.get(reverse("communities:members", args=["alfa"])).status_code, 403)
            self.assertEqual(self.client.get(reverse("communities:invitations", args=["alfa"])).status_code, 200)
            self.assertEqual(self.client.get(reverse("communities:notice_create", args=["alfa"])).status_code, 403)

    def test_moderator_reviews_members_and_publishes_but_does_not_administer(self):
        self.client.force_login(self.moderator)
        self.assertEqual(self.client.get(reverse("communities:members", args=["alfa"])).status_code, 200)
        self.assertEqual(self.client.get(reverse("communities:notice_create", args=["alfa"])).status_code, 200)
        self.assertEqual(self.client.get(reverse("communities:invitations", args=["alfa"])).status_code, 200)
        self.assertEqual(self.client.get(reverse("communities:audit", args=["alfa"])).status_code, 403)

    def test_verified_admin_can_access_administration(self):
        self.verified_login(self.admin)
        for route in ("invitations", "members", "audit"):
            self.assertEqual(self.client.get(reverse(f"communities:{route}", args=["alfa"])).status_code, 200)

    def test_admin_grants_extra_invite_via_endpoint(self):
        self.verified_login(self.admin)
        membership = Membership.objects.get(community=self.community, user=self.member)
        response = self.client.post(
            reverse("communities:membership_extra_invites", args=["alfa", membership.pk]), {"amount": "2"}
        )
        self.assertRedirects(response, reverse("communities:members", args=["alfa"]))
        membership.refresh_from_db()
        self.assertEqual(membership.extra_invites, 2)

    def test_member_cannot_grant_extra_invites_via_endpoint(self):
        self.client.force_login(self.member)
        target = Membership.objects.get(community=self.community, user=self.guest)
        response = self.client.post(
            reverse("communities:membership_extra_invites", args=["alfa", target.pk]), {"amount": "1"}
        )
        self.assertEqual(response.status_code, 403)

    def test_valid_invitation_activates_expected_role(self):
        invitation, raw = create_invitation(
            community=self.community, email=self.outsider.email, role=Membership.Role.GUEST, created_by=self.admin
        )
        membership = accept_invitation(raw_token=raw, user=self.outsider)
        self.assertEqual(membership.status, Membership.Status.ACTIVE)
        self.assertEqual(membership.role, Membership.Role.GUEST)
        invitation.refresh_from_db()
        self.assertEqual(invitation.accepted_by, self.outsider)

    def test_invitation_rejects_wrong_email(self):
        _, raw = create_invitation(
            community=self.community, email="outro@example.invalid", role=Membership.Role.MEMBER, created_by=self.admin
        )
        with self.assertRaisesMessage(FlowError, "e-mail convidado"):
            accept_invitation(raw_token=raw, user=self.outsider)

    def test_invitation_rejects_expired_token(self):
        invitation, raw = create_invitation(
            community=self.community, email=self.outsider.email, role=Membership.Role.MEMBER, created_by=self.admin
        )
        Invitation.objects.filter(pk=invitation.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaisesMessage(FlowError, "não está mais disponível"):
            accept_invitation(raw_token=raw, user=self.outsider)

    def test_invitation_rejects_revoked_token(self):
        invitation, raw = create_invitation(
            community=self.community, email=self.outsider.email, role=Membership.Role.MEMBER, created_by=self.admin
        )
        invitation.revoked_at = timezone.now()
        invitation.save()
        with self.assertRaisesMessage(FlowError, "não está mais disponível"):
            accept_invitation(raw_token=raw, user=self.outsider)

    def test_invitation_is_single_use(self):
        _, raw = create_invitation(
            community=self.community, email=self.outsider.email, role=Membership.Role.MEMBER, created_by=self.admin
        )
        accept_invitation(raw_token=raw, user=self.outsider)
        with self.assertRaisesMessage(FlowError, "não está mais disponível"):
            accept_invitation(raw_token=raw, user=self.outsider)

    def test_suspension_blocks_access_and_reactivation_restores_it(self):
        membership = Membership.objects.get(community=self.community, user=self.member)
        change_membership_status(membership=membership, actor=self.admin, new_status=Membership.Status.SUSPENDED)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("communities:detail", args=["alfa"])).status_code, 403)
        change_membership_status(membership=membership, actor=self.admin, new_status=Membership.Status.ACTIVE)
        self.assertEqual(self.client.get(reverse("communities:detail", args=["alfa"])).status_code, 200)

    def test_notice_publish_and_remove_are_audited(self):
        self.client.force_login(self.moderator)
        response = self.client.post(
            reverse("communities:notice_create", args=["alfa"]), {"title": "Aviso fictício", "body": "Conteúdo de teste"}
        )
        self.assertRedirects(response, reverse("communities:detail", args=["alfa"]))
        notice = Notice.objects.get(title="Aviso fictício")
        self.client.post(reverse("communities:notice_remove", args=["alfa", notice.pk]))
        notice.refresh_from_db()
        self.assertFalse(notice.is_active)
        self.assertTrue(AuditEvent.objects.filter(action="notice.removed", target_id=str(notice.pk)).exists())

    def test_last_admin_cannot_be_demoted_suspended_or_removed(self):
        for operation in (
            lambda: change_membership_role(membership=self.admin_membership, actor=self.admin, new_role=Membership.Role.MEMBER),
            lambda: change_membership_status(membership=self.admin_membership, actor=self.admin, new_status=Membership.Status.SUSPENDED),
            lambda: change_membership_status(membership=self.admin_membership, actor=self.admin, new_status=Membership.Status.REMOVED),
        ):
            with self.assertRaises(FlowError):
                operation()
        self.admin_membership.refresh_from_db()
        self.assertEqual(self.admin_membership.role, Membership.Role.ADMIN)
        self.assertEqual(self.admin_membership.status, Membership.Status.ACTIVE)

    def test_second_admin_allows_role_change_without_touching_other_community(self):
        second = self.join(self.outsider, Membership.Role.ADMIN)
        change_membership_role(membership=second, actor=self.admin, new_role=Membership.Role.MEMBER)
        second.refresh_from_db()
        self.assertEqual(second.role, Membership.Role.MEMBER)
        other_admin = Membership.objects.get(community=self.other, user=self.admin)
        self.assertEqual(other_admin.role, Membership.Role.ADMIN)

    def test_audit_is_immutable_and_filters_sensitive_details(self):
        event = record_event(
            actor=self.admin,
            action="teste.seguro",
            target=self.community,
            community=self.community,
            details={"role": "admin", "email": "nao-salvar@example.invalid", "token": "segredo"},
        )
        self.assertEqual(event.details, {"role": "admin"})
        event.action = "alterado"
        with self.assertRaises(ValueError):
            event.save()
        with self.assertRaises(ValueError):
            event.delete()
