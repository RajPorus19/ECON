from core.config import env_bool, env_str

from .base import *  # noqa: F403

DEBUG = env_bool("DJANGO_DEBUG", True)

# Native `econom start` does not spawn a worker. Run learning inline unless overridden.
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True)
CELERY_TASK_EAGER_PROPAGATES = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("POSTGRES_DB", "econ"),
        "USER": env_str("POSTGRES_USER", "econ"),
        "PASSWORD": env_str("POSTGRES_PASSWORD", "econ"),
        "HOST": env_str("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env_str("POSTGRES_PORT", "5432"),
    }
}
