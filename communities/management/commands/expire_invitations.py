from django.core.management import BaseCommand
from django.utils import timezone

from communities.models import Invitation


class Command(BaseCommand):
    help = "Marca convites vencidos; pode ser executado periodicamente por cron/worker."

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Invitation.objects.filter(
            expires_at__lte=now,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expired_at__isnull=True,
        )
        count = expired.update(expired_at=now, updated_at=now)
        self.stdout.write(self.style.SUCCESS(f"{count} convite(s) expirado(s)."))
