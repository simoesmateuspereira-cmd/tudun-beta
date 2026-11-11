from django.contrib import admin

from .models import Community, Event, Invitation, Membership, MembershipRequest, Notice


class ReadOnlyOperationalAdmin(admin.ModelAdmin):
    """Operações passam pelos serviços com permissões, transações e auditoria."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Community)
class CommunityAdmin(ReadOnlyOperationalAdmin):
    list_display = ("name", "slug", "created_by", "created_at")
    search_fields = ("name", "slug")


@admin.register(Membership)
class MembershipAdmin(ReadOnlyOperationalAdmin):
    list_display = ("community", "user", "role", "status", "joined_at")
    list_filter = ("role", "status", "community")


@admin.register(Invitation)
class InvitationAdmin(ReadOnlyOperationalAdmin):
    list_display = ("community", "email", "role", "state", "expires_at")
    exclude = ("token_hash",)
    readonly_fields = ("accepted_at", "accepted_by", "expired_at", "revoked_at")


@admin.register(MembershipRequest)
class MembershipRequestAdmin(ReadOnlyOperationalAdmin):
    list_display = ("community", "user", "status", "reviewed_by", "reviewed_at")
    list_filter = ("status", "community")


@admin.register(Event)
class EventAdmin(ReadOnlyOperationalAdmin):
    list_display = ("title", "community", "starts_at", "status", "included_in_membership", "price")
    list_filter = ("status", "category", "included_in_membership", "community")
    search_fields = ("title", "slug", "location")


@admin.register(Notice)
class NoticeAdmin(ReadOnlyOperationalAdmin):
    list_display = ("community", "title", "author", "is_active", "created_at")
