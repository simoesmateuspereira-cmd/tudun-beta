import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import manage


class Command(BaseCommand):
    help = "Restaura um backup PostgreSQL local. Exige --confirm RESTAURAR e o caminho do arquivo."

    def add_arguments(self, parser):
        parser.add_argument("backup", type=Path)
        parser.add_argument("--confirm", required=True)

    def handle(self, *args, **options):
        if options["confirm"] != "RESTAURAR":
            raise CommandError("Confirmação inválida. Use --confirm RESTAURAR.")
        backup = options["backup"].resolve()
        if not backup.is_file():
            raise CommandError("Arquivo de backup não encontrado.")
        import pgserver._commands as pg_commands

        database = settings.DATABASES["default"]
        env = os.environ.copy()
        env["PGPASSWORD"] = database["PASSWORD"]
        command = [
            str(pg_commands.POSTGRES_BIN_PATH / "pg_restore.exe"),
            "--clean", "--if-exists", "--no-owner",
            "--host", database["HOST"],
            "--port", database["PORT"],
            "--username", database["USER"],
            "--dbname", database["NAME"],
            manage.short_path(backup),
        ]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        if result.returncode:
            raise CommandError(f"Falha na restauração: {result.stderr.strip()}")
        self.stdout.write(self.style.SUCCESS("Restauração local concluída."))
