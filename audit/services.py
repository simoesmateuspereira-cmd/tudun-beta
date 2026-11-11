from .models import AuditEvent


SAFE_DETAIL_KEYS = {
    "email_domain",
    "role",
    "status",
    "reason",
    "title",
    "expires_at",
    "previous_status",
}


def record_event(*, actor, action, target, community=None, details=None):
    safe_details = {
        key: value
        for key, value in (details or {}).items()
        if key in SAFE_DETAIL_KEYS and isinstance(value, (str, int, float, bool, type(None)))
    }
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        community=community,
        action=action,
        target_type=target.__class__.__name__,
        target_id=str(target.pk),
        details=safe_details,
    )
