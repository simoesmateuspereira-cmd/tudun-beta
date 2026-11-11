from django.shortcuts import redirect
from django.urls import resolve, reverse

from communities.models import Membership


EXEMPT_URL_NAMES = {
    "identity:login",
    "identity:logout",
    "identity:mfa",
    "identity:mfa_recovery",
    "identity:signup",
    "identity:verification_pending",
    "identity:resend_verification",
    "identity:verify_email",
}


def user_requires_mfa(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return Membership.objects.filter(
        user=user,
        role=Membership.Role.ADMIN,
        status=Membership.Status.ACTIVE,
    ).exists()


class AdminMFAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if user_requires_mfa(request.user) and not request.user.is_verified():
            resolver_name = resolve(request.path_info).view_name
            if resolver_name not in EXEMPT_URL_NAMES and not request.path.startswith("/static/"):
                return redirect(reverse("identity:mfa"))
        return self.get_response(request)
