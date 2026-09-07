from core.config import env_bool, env_list, env_str

from .base import *  # noqa: F403

DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env_str("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY must be set in production")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", [])
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set in production")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("POSTGRES_DB", "econ"),
        "USER": env_str("POSTGRES_USER", "econ"),
        "PASSWORD": env_str("POSTGRES_PASSWORD", "econ"),
        "HOST": env_str("POSTGRES_HOST", "postgres"),
        "PORT": env_str("POSTGRES_PORT", "5432"),
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
