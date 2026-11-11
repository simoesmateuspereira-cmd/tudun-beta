from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    community = models.ForeignKey(
        "communities.Community",
        on_delete=models.PROTECT,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80)
    target_id = models.CharField(max_length=80)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["community", "created_at"]), models.Index(fields=["action"])]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Eventos de auditoria não podem ser alterados.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Eventos de auditoria não podem ser excluídos pela aplicação.")

    def __str__(self):
        return f"{self.action} — {self.target_type}:{self.target_id}"
