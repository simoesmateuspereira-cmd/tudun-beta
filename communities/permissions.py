from django.core.exceptions import PermissionDenied

from .models import Membership


def get_active_membership(user, community):
    if not user.is_authenticated:
        return None
    return Membership.objects.filter(
        user=user,
        community=community,
        status=Membership.Status.ACTIVE,
    ).first()


def is_community_admin(user, community):
    membership = get_active_membership(user, community)
    return bool(membership and membership.role == Membership.Role.ADMIN)


def can_view_community(user, community):
    return get_active_membership(user, community) is not None


def can_review_requests(user, community):
    membership = get_active_membership(user, community)
    return bool(membership and membership.role in {Membership.Role.ADMIN, Membership.Role.MODERATOR})


def can_publish_notices(user, community):
    return can_review_requests(user, community)


def can_view_members(user, community):
    return can_review_requests(user, community)


def can_manage_events(user, community):
    return can_review_requests(user, community)


def require_permission(user, community, permission):
    checks = {
        "view": can_view_community,
        "admin": is_community_admin,
        "review": can_review_requests,
        "publish": can_publish_notices,
        "members": can_view_members,
        "events": can_manage_events,
    }
    if not checks[permission](user, community):
        raise PermissionDenied("Você não tem permissão para esta ação.")
