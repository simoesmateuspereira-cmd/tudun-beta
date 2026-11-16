from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone()[0] != 1:
                raise RuntimeError("Resposta inesperada do banco.")
    except Exception:
        return JsonResponse({"status": "indisponivel", "database": "indisponivel"}, status=503)
    return JsonResponse(
        {
            "status": "ok",
            "database": "ok",
            "debug_headers": {
                "x_forwarded_proto": request.META.get("HTTP_X_FORWARDED_PROTO"),
                "x_forwarded_host": request.META.get("HTTP_X_FORWARDED_HOST"),
                "x_forwarded_for": request.META.get("HTTP_X_FORWARDED_FOR"),
                "is_secure": request.is_secure(),
            },
        }
    )
