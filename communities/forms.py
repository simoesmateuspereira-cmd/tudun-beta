from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from .models import Community, Event, Invitation, Membership, Notice


class CommunityForm(forms.ModelForm):
    admin_email = forms.EmailField(
        label="E-mail do administrador",
        help_text="A conta precisa existir e ter o e-mail verificado.",
    )

    class Meta:
        model = Community
        fields = ["name", "slug", "description"]
        labels = {"name": "Nome", "slug": "Identificador único", "description": "Descrição"}
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, creator=None, **kwargs):
        super().__init__(*args, **kwargs)
        if creator and not self.is_bound:
            self.fields["admin_email"].initial = creator.email

    def clean_slug(self):
        slug = slugify(self.cleaned_data["slug"])
        if not slug:
            raise forms.ValidationError("Use letras ou números para formar o identificador.")
        return slug

    def clean_admin_email(self):
        email = self.cleaned_data["admin_email"].strip().lower()
        user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            raise forms.ValidationError("Não existe uma conta ativa com este e-mail.")
        profile = getattr(user, "identity_profile", None)
        if not profile or not profile.email_is_verified:
            raise forms.ValidationError("O administrador precisa verificar o e-mail antes.")
        return email


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "category",
            "location",
            "starts_at",
            "ends_at",
            "capacity",
            "included_in_membership",
            "price",
            "status",
            "is_featured",
        ]
        labels = {
            "title": "Nome do evento",
            "description": "Descrição",
            "category": "Categoria",
            "location": "Local",
            "starts_at": "Início",
            "ends_at": "Término",
            "capacity": "Capacidade",
            "included_in_membership": "Incluído na assinatura",
            "price": "Preço (R$)",
            "status": "Situação",
            "is_featured": "Destacar na agenda",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "starts_at": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, community=None, **kwargs):
        super().__init__(*args, **kwargs)
        if community is not None:
            self.instance.community = community
        self.fields["price"].required = False
        self.fields["price"].help_text = "Deixe em branco para eventos gratuitos ou incluídos na assinatura."
        for field_name in ("starts_at", "ends_at"):
            self.fields[field_name].input_formats = ["%Y-%m-%dT%H:%M", "%d/%m/%Y %H:%M"]

    def clean_price(self):
        return self.cleaned_data.get("price") or 0


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ["email", "role"]
        labels = {"email": "E-mail convidado (opcional)", "role": "Perfil após o aceite"}
        help_texts = {
            "email": "Se preencher, só esse e-mail consegue usar o link. Se deixar em branco, qualquer pessoa com o link pode entrar."
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False
        self.fields["role"].choices = [
            (Membership.Role.MEMBER, "Membro"),
            (Membership.Role.GUEST, "Convidado"),
        ]


class ReviewForm(forms.Form):
    reason = forms.CharField(
        label="Motivo ou observação",
        required=False,
        max_length=800,
        widget=forms.Textarea(attrs={"rows": 4}),
    )


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ["title", "body"]
        labels = {"title": "Título", "body": "Conteúdo"}
        widgets = {"body": forms.Textarea(attrs={"rows": 6})}


class MembershipRoleForm(forms.Form):
    role = forms.ChoiceField(label="Novo perfil", choices=Membership.Role.choices)
