from django.conf import settings
from django.db import models


class IdentityProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="identity_profile")
    email_verified_at = models.DateTimeField(null=True, blank=True)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "perfil de identidade"
        verbose_name_plural = "perfis de identidade"

    @property
    def email_is_verified(self):
        return self.email_verified_at is not None

    def __str__(self):
        return f"Identidade de {self.user}"
