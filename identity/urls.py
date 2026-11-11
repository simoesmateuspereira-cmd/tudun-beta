from django.urls import path

from . import views
from .ratelimit import rate_limit

app_name = "identity"

urlpatterns = [
    path("entrar/", rate_limit(rate="5/m")(views.SignInView.as_view()), name="login"),
    path("sair/", views.SignOutView.as_view(), name="logout"),
    path("criar-conta/", views.signup, name="signup"),
    path("verificacao-pendente/", views.verification_pending, name="verification_pending"),
    path("reenviar-verificacao/", views.resend_verification, name="resend_verification"),
    path("verificar-email/<str:token>/", views.verify_email, name="verify_email"),
    path("privacidade/", views.privacy, name="privacy"),
    path("mfa/", views.mfa_gate, name="mfa"),
    path("mfa/recuperacao/", views.mfa_recovery, name="mfa_recovery"),
    path("mfa/regerar/", views.mfa_reissue_recovery, name="mfa_reissue"),
]
