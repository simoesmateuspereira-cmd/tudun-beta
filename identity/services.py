import base64
import binascii
import logging

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from audit.services import record_event

from .models import IdentityProfile


logger = logging.getLogger("identity.security")
EMAIL_VERIFICATION_SALT = "identity.email-verification.v1"


def profile_for(user):
    profile, _ = IdentityProfile.objects.get_or_create(user=user)
    return profile


def email_is_verified(user):
    if not user.is_authenticated:
        return False
    return profile_for(user).email_is_verified


def send_verification_email(*, user, request):
    email = user.email.strip().lower()
    if not email:
        raise ValueError("A conta precisa de um e-mail para verificação.")
    if user.email != email:
        user.email = email
        user.save(update_fields=["email"])

    signed_token = signing.dumps(
        {"user_id": user.pk, "email": email},
        salt=EMAIL_VERIFICATION_SALT,
        compress=True,
    )
    # Remove os dois-pontos do formato assinado: além de URL-safe, evita que
    # handlers de arquivos estáticos do Windows interpretem o caminho como drive.
    token = base64.urlsafe_b64encode(signed_token.encode("ascii")).decode("ascii").rstrip("=")
    verification_url = request.build_absolute_uri(reverse("identity:verify_email", kwargs={"token": token}))
    send_mail(
        subject="Confirme seu e-mail de teste no TUDUN",
        message=(
            "Confirme o e-mail da sua conta no ambiente de teste do TUDUN.\n\n"
            f"Acesse: {verification_url}\n\n"
            f"Este link expira em {settings.EMAIL_VERIFICATION_MAX_AGE // 3600} horas. "
            "Se você não criou esta conta, ignore esta mensagem."
        ),
        from_email=None,
        recipient_list=[email],
    )
    profile = profile_for(user)
    profile.verification_sent_at = timezone.now()
    profile.save(update_fields=["verification_sent_at", "updated_at"])
    record_event(
        actor=user,
        action="identity.verification_sent",
        target=user,
        details={"email_domain": email.rsplit("@", 1)[-1]},
    )
    logger.info("E-mail de verificação enviado para user_id=%s", user.pk)


def verify_email_token(token):
    """Retorna (usuário, já estava verificado) ou propaga erro de assinatura."""
    try:
        signed_token = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode("ascii")
    except (binascii.Error, UnicodeDecodeError):
        # Mantém compatibilidade com links locais emitidos antes da codificação.
        signed_token = token
    payload = signing.loads(
        signed_token,
        salt=EMAIL_VERIFICATION_SALT,
        max_age=settings.EMAIL_VERIFICATION_MAX_AGE,
    )
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(pk=payload.get("user_id"), is_active=True).first()
    if not user or user.email.strip().lower() != payload.get("email", "").lower():
        raise signing.BadSignature("A conta ou o e-mail associado ao link mudou.")
    profile = profile_for(user)
    already_verified = profile.email_is_verified
    if not already_verified:
        profile.email_verified_at = timezone.now()
        profile.save(update_fields=["email_verified_at", "updated_at"])
        record_event(actor=user, action="identity.email_verified", target=user)
        logger.info("E-mail verificado para user_id=%s", user.pk)
    return user, already_verified
