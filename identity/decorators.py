from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .services import email_is_verified


def email_verified_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not email_is_verified(request.user):
            messages.warning(request, "Confirme seu e-mail antes de continuar.")
            return redirect("identity:verification_pending")
        return view_func(request, *args, **kwargs)

    return wrapped
