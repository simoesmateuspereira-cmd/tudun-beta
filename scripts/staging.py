"""Homologação local com DEBUG=False e Waitress, sem exposição externa."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import manage


parser = argparse.ArgumentParser()
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=7101)
args = parser.parse_args()

# Estas exceções permitem testar HTTP apenas em loopback. Um Beta externo
# precisa de HTTPS e deve remover os quatro overrides abaixo.
os.environ["DJANGO_DEBUG"] = "False"
os.environ.setdefault("SECURE_SSL_REDIRECT", "False")
os.environ.setdefault("SESSION_COOKIE_SECURE", "False")
os.environ.setdefault("CSRF_COOKIE_SECURE", "False")
os.environ.setdefault("SECURE_HSTS_SECONDS", "0")
os.environ.setdefault("EMAIL_BACKEND", "django.core.mail.backends.filebased.EmailBackend")
manage.prepare_development_environment()

import django
from django.core.management import call_command
from waitress import serve


django.setup()
call_command("migrate", interactive=False, verbosity=1)
call_command("collectstatic", interactive=False, clear=False, verbosity=0)
from config.wsgi import application


print(f"Homologação local em http://{args.host}:{args.port} (somente dados fictícios).")
serve(
    application,
    host=args.host,
    port=args.port,
    threads=8,
    connection_limit=100,
    channel_timeout=30,
    cleanup_interval=10,
    max_request_body_size=1_048_576,
)
