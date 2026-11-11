from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from audit.services import record_event


class Command(BaseCommand):
    help = "Redefine MFA após verificação presencial/documentada pelo responsável local."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--confirm", required=True, help="Digite REDEFINIR para confirmar.")

    def handle(self, *args, **options):
        if options["confirm"] != "REDEFINIR":
            raise CommandError("Confirmação inválida.")
        user = get_user_model().objects.filter(username=options["username"]).first()
        if not user:
            raise CommandError("Usuário não encontrado.")
        TOTPDevice.objects.filter(user=user).delete()
        StaticDevice.objects.filter(user=user).delete()
        record_event(actor=None, action="identity.mfa_reset", target=user)
        self.stdout.write(self.style.SUCCESS("MFA redefinido; será exigido novo cadastro no próximo acesso."))
