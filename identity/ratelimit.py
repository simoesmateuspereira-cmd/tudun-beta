from functools import wraps

from django.shortcuts import render
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited


def rate_limit(*, rate, key="ip"):
    """Limita somente escritas e devolve 429 sem executar a operação bloqueada."""
    def decorator(view_func):
        limited_view = ratelimit(key=key, rate=rate, method="POST", block=True)(view_func)

        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            try:
                return limited_view(request, *args, **kwargs)
            except Ratelimited:
                return render(request, "identity/rate_limited.html", status=429)

        return wrapped

    return decorator
