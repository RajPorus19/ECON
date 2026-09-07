"""Shared Django settings for ECON."""

from pathlib import Path

from dotenv import load_dotenv

from core.config import env_float, env_int, env_list, env_str

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = env_str("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.users",
    "apps.knowledge",
    "apps.flows",
    "apps.execution",
    "apps.llm",
    "apps.requests",
    "apps.plugins",
    "apps.analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}

CELERY_BROKER_URL = env_str("CELERY_BROKER_URL", env_str("REDIS_URL", "redis://127.0.0.1:6379/1"))
CELERY_RESULT_BACKEND = env_str("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_TASK_ALWAYS_EAGER = False

ECON = {
    "LLM_BASE_URL": env_str("ECON_LLM_BASE_URL", "http://127.0.0.1:11434"),
    "LLM_MODEL": env_str("ECON_LLM_MODEL", "hermes"),
    "CONFIDENCE_THRESHOLD": env_float("ECON_CONFIDENCE_THRESHOLD", 0.90),
    "EXECUTION_TIMEOUT": env_int("ECON_EXECUTION_TIMEOUT", 30),
    "EXECUTION_MODE": env_str("ECON_EXECUTION_MODE", "local"),
    "HOST_AGENT_URL": env_str("ECON_HOST_AGENT_URL", "http://127.0.0.1:8765"),
    "HOST_AGENT_TOKEN": env_str("ECON_HOST_AGENT_TOKEN", ""),
}

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://localhost:3000", "http://127.0.0.1:3000"],
)
