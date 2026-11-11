#!/usr/bin/env python
import os
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
_PGSERVER = None


def short_path(path):
    """Contorna limitações de codificação do PostgreSQL em pastas Windows."""
    path = str(path)
    if os.name == "nt":
        import ctypes

        buffer = ctypes.create_unicode_buffer(260)
        result = ctypes.windll.kernel32.GetShortPathNameW(path, buffer, 260)
        if result:
            return buffer.value
    return path


def postgres_data_path():
    configured = os.environ.get("TUDUN_POSTGRES_DATA_DIR")
    if configured:
        return short_path(Path(configured).resolve())
    # A cópia recuperada preserva o cluster original e evita processos residuais do Windows.
    recovered = BASE_DIR / ".postgres-recovered"
    return short_path(recovered if recovered.exists() else BASE_DIR / ".postgres")


def prepare_development_environment():
    global _PGSERVER
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    if not os.environ.get("DJANGO_SECRET_KEY"):
        runtime_dir = BASE_DIR / ".runtime"
        runtime_dir.mkdir(exist_ok=True)
        secret_file = runtime_dir / ".django-secret"
        if not secret_file.exists():
            secret_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        os.environ["DJANGO_SECRET_KEY"] = secret_file.read_text(encoding="utf-8").strip()

    if not os.environ.get("DATABASE_URL"):
        import pgserver
        import pgserver._commands as pg_commands
        import pgserver.postgres_server as pg_runtime

        # Recuperação após encerramento abrupto pode exceder os 10 s do pgserver.
        original_pg_ctl = pg_runtime.pg_ctl

        def patient_pg_ctl(args, **kwargs):
            if "start" in args:
                kwargs["timeout"] = 60
                # O Windows não consegue sincronizar um log aberto dentro de PGDATA.
                # Um arquivo por execução também evita conflitos com prévias e testes paralelos.
                args = list(args)
                log_path = BASE_DIR / ".runtime" / f"postgres-{os.getpid()}.log"
                args[args.index("-l") + 1] = short_path(log_path)
            return original_pg_ctl(args, **kwargs)

        pg_runtime.pg_ctl = patient_pg_ctl

        if os.name == "nt":
            install_alias = BASE_DIR / ".runtime" / "pginstall"
            if not install_alias.exists():
                import subprocess

                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(install_alias), str(pg_commands.POSTGRES_BIN_PATH.parent)],
                    check=True,
                    capture_output=True,
                )
            pg_commands.POSTGRES_BIN_PATH = pg_commands.Path(short_path(install_alias / "bin"))
        # Instanciar diretamente evita que get_server().resolve() desfaça o alias ASCII.
        _PGSERVER = pg_runtime.PostgresServer(
            pg_commands.Path(postgres_data_path()), cleanup_mode="stop"
        )
        os.environ["DATABASE_URL"] = _PGSERVER.get_uri()


def main():
    prepare_development_environment()
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
