"""Middlewares de infraestrutura da TUDUN."""


class ForceHttpsSchemeMiddleware:
    """Trata toda requisição como HTTPS quando o app roda atrás de um proxy
    de terminação SSL que não repassa X-Forwarded-Proto (Render Free).

    Nesse cenário o container só é alcançável pelo proxy da plataforma, que
    já termina o TLS na URL pública; sem esse middleware o Django marca
    request.is_secure() como False e quebra SECURE_SSL_REDIRECT, cookies
    seguros e HSTS.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.META["wsgi.url_scheme"] = "https"
        return self.get_response(request)
