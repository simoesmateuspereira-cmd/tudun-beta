import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "identity",
    "communities",
    "audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "identity.middleware.AdminMFAMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if env_bool("DJANGO_FORCE_HTTPS_SCHEME"):
    # Proxy de terminação SSL que não repassa X-Forwarded-Proto (Render Free).
    MIDDLEWARE.insert(0, "config.middleware.ForceHttpsSchemeMiddleware")
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

database_url = urlparse(os.environ["DATABASE_URL"])
database_options = {"connect_timeout": 5}
database_sslmode = os.getenv("DATABASE_SSLMODE", "").strip()
if database_sslmode:
    database_options["sslmode"] = database_sslmode
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_url.path.lstrip("/") or "postgres",
        "USER": unquote(database_url.username or "postgres"),
        "PASSWORD": unquote(database_url.password or ""),
        "HOST": database_url.hostname or "localhost",
        "PORT": str(database_url.port or 5432),
        # O pacote local do PostgreSQL não inclui a base IANA; GMT equivale a UTC.
        "TIME_ZONE": os.getenv("DATABASE_TIME_ZONE", "GMT"),
        "CONN_MAX_AGE": int(os.getenv("DATABASE_CONN_MAX_AGE", "0")),
        "OPTIONS": database_options,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / ".collected_static"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "identity:login"
LOGIN_REDIRECT_URL = "communities:home"
LOGOUT_REDIRECT_URL = "communities:home"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 28800
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if env_bool("DJANGO_TRUST_PROXY_SSL") else None
X_FRAME_OPTIONS = "DENY"

CACHE_URL = os.getenv("CACHE_URL", "").strip()
CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "tudun")
if CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": CACHE_URL,
            "KEY_PREFIX": CACHE_KEY_PREFIX,
            "OPTIONS": {
                "socket_connect_timeout": 3,
                "socket_timeout": 3,
                "health_check_interval": 30,
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "tudun-local",
            "KEY_PREFIX": CACHE_KEY_PREFIX,
        }
    }

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.filebased.EmailBackend")
EMAIL_FILE_PATH = BASE_DIR / ".runtime" / "outbox"
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "tudun-teste@localhost")
EMAIL_VERIFICATION_MAX_AGE = int(os.getenv("EMAIL_VERIFICATION_MAX_AGE", "172800"))
OTP_TOTP_ISSUER = "TUDUN"

from django.core.exceptions import ImproperlyConfigured

if env_bool("DJANGO_REQUIRE_SHARED_CACHE") and not CACHE_URL:
    raise ImproperlyConfigured("DJANGO_REQUIRE_SHARED_CACHE exige CACHE_URL com um Redis compartilhado.")
if env_bool("DJANGO_REQUIRE_SMTP"):
    smtp_ready = EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and EMAIL_HOST
    gmail_ready = EMAIL_BACKEND == "identity.gmail_backend.GmailAPIBackend" and all(
        os.getenv(name, "").strip()
        for name in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")
    )
    if not DEFAULT_FROM_EMAIL or not (smtp_ready or gmail_ready):
        raise ImproperlyConfigured(
            "DJANGO_REQUIRE_SMTP exige SMTP completo ou Gmail API completo, além de DEFAULT_FROM_EMAIL."
        )

RATELIMIT_ENABLE = env_bool("RATELIMIT_ENABLE", True)
RATELIMIT_USE_CACHE = os.getenv("RATELIMIT_USE_CACHE", "default")

LOG_TO_FILE = env_bool("LOG_TO_FILE", True)
LOG_DIR = BASE_DIR / ".runtime" / "logs"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact_sensitive_paths": {"()": "identity.logging.RedactSensitivePathsFilter"}},
    "formatters": {"standard": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "filters": ["redact_sensitive_paths"],
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "identity.security": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
if LOG_TO_FILE:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOGGING["handlers"]["application_file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": LOG_DIR / "tudun.log",
        "maxBytes": 2_000_000,
        "backupCount": 3,
        "encoding": "utf-8",
        "formatter": "standard",
        "filters": ["redact_sensitive_paths"],
    }
    LOGGING["root"]["handlers"].append("application_file")
    for logger in LOGGING["loggers"].values():
        logger["handlers"].append("application_file")
