from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Community(TimeStampedModel):
    name = models.CharField("nome", max_length=120)
    slug = models.SlugField("identificador", max_length=140, unique=True)
    description = models.TextField("descrição", max_length=1200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="communities_created",
    )

    class Meta:
        verbose_name = "comunidade"
        verbose_name_plural = "comunidades"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        MODERATOR = "moderator", "Moderador"
        MEMBER = "member", "Membro"
        GUEST = "guest", "Convidado"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        ACTIVE = "active", "Ativo"
        SUSPENDED = "suspended", "Suspenso"
        REMOVED = "removed", "Removido"
        DECLINED = "declined", "Recusado"

    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField("perfil", max_length=20, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField("situação", max_length=20, choices=Status.choices, default=Status.PENDING)
    joined_at = models.DateTimeField("entrada", null=True, blank=True)
    extra_invites = models.PositiveIntegerField("convites extras", default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["community", "user"], name="unique_membership_per_community")
        ]
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["community", "role", "status"])]
        ordering = ["user__username"]

    def activate(self, role=None):
        self.status = self.Status.ACTIVE
        self.joined_at = self.joined_at or timezone.now()
        if role:
            self.role = role

    def __str__(self):
        return f"{self.user} em {self.community}"


class Invitation(TimeStampedModel):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField("e-mail", blank=True, default="")
    role = models.CharField("perfil", max_length=20, choices=Membership.Role.choices, default=Membership.Role.MEMBER)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField("expira em")
    expired_at = models.DateTimeField("expirado em", null=True, blank=True)
    revoked_at = models.DateTimeField("revogado em", null=True, blank=True)
    accepted_at = models.DateTimeField("aceito em", null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_invitations",
    )

    class Meta:
        indexes = [models.Index(fields=["community", "email"]), models.Index(fields=["expires_at"])]
        ordering = ["-created_at"]

    @property
    def state(self):
        if self.revoked_at:
            return "revogado"
        if self.accepted_at:
            return "aceito"
        if self.expires_at <= timezone.now():
            return "expirado"
        return "pendente"

    def clean(self):
        if self.role not in {Membership.Role.MEMBER, Membership.Role.GUEST}:
            raise ValidationError({"role": "Convites só podem criar membros ou convidados."})

    def __str__(self):
        return f"Convite para {self.email} — {self.community}"


class MembershipRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovada"
        DECLINED = "declined", "Recusada"

    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="membership_requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membership_requests")
    message = models.TextField("mensagem", max_length=800, blank=True)
    status = models.CharField("situação", max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_membership_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_reason = models.TextField("motivo da decisão", max_length=800, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["community", "user"], name="unique_request_per_community")
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"Solicitação de {self.user} — {self.community}"


class Event(TimeStampedModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponível"
        LAST_SEATS = "last_seats", "Últimas vagas"
        SOLD_OUT = "sold_out", "Esgotado"
        CANCELLED = "cancelled", "Cancelado"

    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="events")
    title = models.CharField("título", max_length=180)
    slug = models.SlugField("identificador", max_length=200)
    description = models.TextField("descrição", max_length=4000)
    category = models.CharField("categoria", max_length=80)
    location = models.CharField("local", max_length=240)
    starts_at = models.DateTimeField("início")
    ends_at = models.DateTimeField("término")
    capacity = models.PositiveIntegerField("capacidade")
    price = models.DecimalField("preço", max_digits=10, decimal_places=2, default=0)
    included_in_membership = models.BooleanField("incluído na assinatura", default=False)
    status = models.CharField("situação", max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    is_featured = models.BooleanField("destaque", default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="events_created",
    )

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventos"
        constraints = [
            models.UniqueConstraint(fields=["community", "slug"], name="unique_event_slug_per_community")
        ]
        indexes = [models.Index(fields=["community", "starts_at", "status"])]
        ordering = ["starts_at", "title"]

    def clean(self):
        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "O término deve ser posterior ao início."})
        if self.included_in_membership and self.price:
            raise ValidationError({"price": "Eventos incluídos na assinatura não devem ter preço adicional."})

    def __str__(self):
        return f"{self.title} — {self.community}"


class Notice(TimeStampedModel):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="notices")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notices")
    title = models.CharField("título", max_length=160)
    body = models.TextField("conteúdo", max_length=4000)
    is_active = models.BooleanField("publicado", default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
