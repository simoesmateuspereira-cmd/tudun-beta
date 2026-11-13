import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class ProductionSettingsTests(SimpleTestCase):
    def load_settings(self, snippet, **overrides):
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_SETTINGS_MODULE": "config.settings",
                "DJANGO_DEBUG": "False",
                "CACHE_URL": "",
                "DJANGO_REQUIRE_SHARED_CACHE": "False",
                "DJANGO_REQUIRE_SMTP": "False",
                "LOG_TO_FILE": "False",
            }
        )
        env.update(overrides)
        return subprocess.run(
            [sys.executable, "-c", f"from config import settings; {snippet}"],
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_local_fallback_is_explicit(self):
        result = self.load_settings("print(settings.CACHES['default']['BACKEND'])", DJANGO_DEBUG="True")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "django.core.cache.backends.locmem.LocMemCache")

    def test_database_sslmode_is_configurable(self):
        result = self.load_settings(
            "print(settings.DATABASES['default']['OPTIONS']['sslmode'])",
            DATABASE_SSLMODE="require",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "require")

    def test_redis_url_selects_shared_cache_with_key_prefix(self):
        result = self.load_settings(
            "print(settings.CACHES['default']['BACKEND']); "
            "print(settings.CACHES['default']['LOCATION']); print(settings.CACHES['default']['KEY_PREFIX'])",
            CACHE_URL="rediss://cache.example.invalid:6379/0",
            CACHE_KEY_PREFIX="tudun-teste",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "django.core.cache.backends.redis.RedisCache",
                "rediss://cache.example.invalid:6379/0",
                "tudun-teste",
            ],
        )

    def test_required_shared_cache_rejects_local_fallback(self):
        result = self.load_settings("pass", DJANGO_REQUIRE_SHARED_CACHE="True")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_REQUIRE_SHARED_CACHE exige CACHE_URL", result.stderr)

    def test_required_smtp_rejects_file_email_backend(self):
        result = self.load_settings(
            "pass",
            DJANGO_REQUIRE_SMTP="True",
            EMAIL_BACKEND="django.core.mail.backends.filebased.EmailBackend",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_REQUIRE_SMTP exige", result.stderr)

    def test_required_email_accepts_complete_gmail_api_configuration(self):
        result = self.load_settings(
            "print(settings.EMAIL_BACKEND)",
            DJANGO_REQUIRE_SMTP="True",
            EMAIL_BACKEND="identity.gmail_backend.GmailAPIBackend",
            GMAIL_CLIENT_ID="cliente-teste",
            GMAIL_CLIENT_SECRET="segredo-teste",
            GMAIL_REFRESH_TOKEN="renovacao-teste",
            DEFAULT_FROM_EMAIL="remetente@gmail.com",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "identity.gmail_backend.GmailAPIBackend")

    def test_required_email_rejects_incomplete_gmail_api_configuration(self):
        result = self.load_settings(
            "pass",
            DJANGO_REQUIRE_SMTP="True",
            EMAIL_BACKEND="identity.gmail_backend.GmailAPIBackend",
            GMAIL_CLIENT_ID="",
            GMAIL_CLIENT_SECRET="",
            GMAIL_REFRESH_TOKEN="",
            DEFAULT_FROM_EMAIL="remetente@gmail.com",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Gmail API completo", result.stderr)

    def test_hosted_logs_use_console_only(self):
        result = self.load_settings(
            "print(settings.LOGGING['root']['handlers']); print('application_file' in settings.LOGGING['handlers'])"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["['console']", "False"])
