"""Inicialização provider-neutral para hospedagem gerenciada do Beta."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

parser = argparse.ArgumentParser()
parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
mode = parser.add_mutually_exclusive_group()
mode.add_argument("--validate-only", action="store_true")
mode.add_argument("--release-only", action="store_true")
mode.add_argument("--serve-only", action="store_true")
args = parser.parse_args()

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_DEBUG"] = "False"
os.environ["DJANGO_REQUIRE_SHARED_CACHE"] = "True"
os.environ["DJANGO_REQUIRE_SMTP"] = "True"
os.environ["LOG_TO_FILE"] = "False"
os.environ.setdefault("DJANGO_TRUST_PROXY_SSL", "True")
os.environ.setdefault("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")

required = (
    "DJANGO_SECRET_KEY",
    "DATABASE_URL",
    "CACHE_URL",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "EMAIL_HOST",
    "DEFAULT_FROM_EMAIL",
)
missing = [name for name in required if not os.getenv(name, "").strip()]
if missing:
    raise RuntimeError("Variáveis obrigatórias ausentes: " + ", ".join(missing))

import django
from django.core.management import call_command

django.setup()
call_command("check")
if args.validate_only:
    print("Configuração de produção validada; nenhum servidor foi iniciado.")
    raise SystemExit(0)

if not args.serve_only:
    # Em plataformas com release separado, execute esta etapa uma única vez.
    call_command("migrate", interactive=False, verbosity=1)
    call_command("collectstatic", interactive=False, clear=False, verbosity=0)
    if args.release_only:
        print("Release concluída; nenhum servidor foi iniciado.")
        raise SystemExit(0)

from config.wsgi import application
from waitress import serve

serve(
    application,
    host=args.host,
    port=args.port,
    threads=int(os.getenv("WAITRESS_THREADS", "8")),
    connection_limit=int(os.getenv("WAITRESS_CONNECTION_LIMIT", "100")),
    channel_timeout=30,
    cleanup_interval=10,
    max_request_body_size=1_048_576,
)
