import base64
import io
import logging

import qrcode
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core import signing
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_otp import login as otp_login
from django_otp import match_token
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from communities.services import FlowError, accept_invitation, get_invitation_by_token

from .forms import SignUpForm, TokenForm
from .middleware import user_requires_mfa
from .ratelimit import rate_limit
from .services import email_is_verified, profile_for, send_verification_email, verify_email_token


logger = logging.getLogger("identity.security")


class SignInView(LoginView):
    template_name = "identity/login.html"
    redirect_authenticated_user = True


class SignOutView(LogoutView):
    next_page = reverse_lazy("communities:home")


def _invitation_is_usable(invitation):
    if invitation is None:
        return False
    return (
        invitation.revoked_at is None
        and invitation.accepted_at is None
        and invitation.expired_at is None
        and invitation.expires_at > timezone.now()
    )


@rate_limit(rate="5/m")
def signup(request):
    if request.user.is_authenticated:
        return redirect("communities:home")

    raw_token = request.POST.get("invite_token") or request.GET.get("convite") or ""
    invitation = get_invitation_by_token(raw_token)
    if not _invitation_is_usable(invitation):
        return render(request, "identity/signup_closed.html", status=403)

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error("email", "Já existe uma conta com este e-mail.")
        else:
            profile_for(user)
            try:
                membership = accept_invitation(raw_token=raw_token, user=user)
            except FlowError as exc:
                user.delete()
                form.add_error(None, str(exc))
            else:
                login(request, user)
                try:
                    send_verification_email(user=user, request=request)
                except Exception:
                    logger.exception("Falha no envio de verificação para user_id=%s", user.pk)
                    messages.warning(request, "Conta criada, mas o envio do e-mail de confirmação falhou. Use a opção de reenvio.")
                else:
                    messages.success(request, f"Bem-vindo(a) à {membership.community.name}! Confira a caixa de e-mail para confirmar o endereço.")
                return redirect("communities:detail", slug=membership.community.slug)
    return render(
        request,
        "identity/signup.html",
        {"form": form, "invite_token": raw_token, "community": invitation.community},
    )


@login_required
def verification_pending(request):
    if email_is_verified(request.user):
        return redirect("communities:home")
    return render(request, "identity/verification_pending.html")


@login_required
@require_POST
@rate_limit(rate="3/m", key="user_or_ip")
def resend_verification(request):
    if email_is_verified(request.user):
        messages.info(request, "Seu e-mail já está confirmado.")
        return redirect("communities:home")
    try:
        send_verification_email(user=request.user, request=request)
    except Exception:
        logger.exception("Falha no reenvio de verificação para user_id=%s", request.user.pk)
        messages.error(request, "Não foi possível reenviar agora. Tente novamente mais tarde.")
    else:
        messages.success(request, "Nova verificação enviada.")
    return redirect("identity:verification_pending")


def verify_email(request, token):
    try:
        user, already_verified = verify_email_token(token)
    except signing.SignatureExpired:
        messages.error(request, "Este link de verificação expirou. Entre na conta e solicite um novo.")
    except signing.BadSignature:
        messages.error(request, "Este link de verificação é inválido ou não corresponde mais à conta.")
    else:
        messages.info(request, "Seu e-mail já estava confirmado.") if already_verified else messages.success(
            request, "E-mail confirmado com sucesso."
        )
        return redirect("communities:home" if request.user.is_authenticated else "identity:login")
    return redirect("identity:verification_pending" if request.user.is_authenticated else "identity:login")


def privacy(request):
    return render(request, "identity/privacy.html")


def _new_recovery_codes(user):
    StaticDevice.objects.filter(user=user).delete()
    device = StaticDevice.objects.create(user=user, name="Códigos de recuperação", confirmed=True)
    codes = [StaticToken.random_token() for _ in range(10)]
    for code in codes:
        device.token_set.create(token=code)
    return codes


def _qr_data_uri(config_url):
    image = qrcode.make(config_url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


@login_required
@rate_limit(rate="10/m", key="user_or_ip")
def mfa_gate(request):
    user = request.user
    if not user_requires_mfa(user) or user.is_verified():
        return redirect("communities:home")

    confirmed_device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    form = TokenForm(request.POST or None)
    setup_mode = confirmed_device is None
    setup_device = None
    qr_data_uri = None

    if setup_mode:
        setup_device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if setup_device is None:
            setup_device = TOTPDevice.objects.create(user=user, name="Aplicativo autenticador", confirmed=False)
        qr_data_uri = _qr_data_uri(setup_device.config_url)

    if request.method == "POST" and form.is_valid():
        token = form.cleaned_data["token"]
        if setup_mode:
            if setup_device.verify_token(token):
                setup_device.confirmed = True
                setup_device.save()
                request.session["mfa_recovery_codes"] = _new_recovery_codes(user)
                otp_login(request, setup_device)
                messages.success(request, "MFA ativado. Guarde os códigos de recuperação.")
                return redirect("identity:mfa_recovery")
            messages.error(request, "Código inválido. Confira o aplicativo e tente novamente.")
        else:
            device = match_token(user, token)
            if device:
                otp_login(request, device)
                messages.success(request, "Identidade confirmada.")
                return redirect("communities:home")
            messages.error(request, "Código inválido ou já utilizado.")

    return render(
        request,
        "identity/mfa.html",
        {
            "form": form,
            "setup_mode": setup_mode,
            "qr_data_uri": qr_data_uri,
            "setup_device": setup_device,
        },
    )


@login_required
def mfa_recovery(request):
    codes = request.session.get("mfa_recovery_codes")
    if not codes:
        return redirect("communities:home")
    if request.method == "POST":
        request.session.pop("mfa_recovery_codes", None)
        messages.success(request, "Códigos de recuperação confirmados.")
        return redirect("communities:home")
    return render(request, "identity/recovery.html", {"codes": codes})


@login_required
def mfa_reissue_recovery(request):
    if request.method != "POST" or not request.user.is_verified() or not user_requires_mfa(request.user):
        return redirect("identity:mfa")
    request.session["mfa_recovery_codes"] = _new_recovery_codes(request.user)
    messages.warning(request, "Os códigos anteriores foram invalidados.")
    return redirect("identity:mfa_recovery")
