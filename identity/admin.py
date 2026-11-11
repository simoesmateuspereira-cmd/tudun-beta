from django.contrib import admin

from .models import IdentityProfile


@admin.register(IdentityProfile)
class IdentityProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email_verified_at", "verification_sent_at", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("user", "email_verified_at", "verification_sent_at", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
