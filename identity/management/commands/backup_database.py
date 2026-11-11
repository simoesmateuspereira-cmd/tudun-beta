import os
import subprocess
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import manage


class Command(BaseCommand):
    help = "Gera backup PostgreSQL local em formato custom, sem enviar dados para fora da máquina."

    def handle(self, *args, **options):
        import pgserver._commands as pg_commands

        backup_dir = manage.BASE_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        destination = backup_dir / f"tudun-{datetime.now():%Y%m%d-%H%M%S}.dump"
        database = settings.DATABASES["default"]
        env = os.environ.copy()
        env["PGPASSWORD"] = database["PASSWORD"]
        command = [
            str(pg_commands.POSTGRES_BIN_PATH / "pg_dump.exe"),
            "--format=custom",
            "--host", database["HOST"],
            "--port", database["PORT"],
            "--username", database["USER"],
            "--file", manage.short_path(destination),
            database["NAME"],
        ]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        if result.returncode:
            raise CommandError(f"Falha no backup: {result.stderr.strip()}")
        if not destination.exists() or destination.stat().st_size == 0:
            raise CommandError("O backup não foi criado corretamente.")
        self.stdout.write(self.style.SUCCESS(f"Backup local criado: {destination}"))
