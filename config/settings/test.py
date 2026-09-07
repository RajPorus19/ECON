from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = "test-secret-key"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

ECON = {
    **ECON,  # noqa: F405
    "LLM_BASE_URL": "http://127.0.0.1:11434",
    "LLM_MODEL": "hermes",
    "EXECUTION_MODE": "local",
    "HOST_AGENT_URL": "http://127.0.0.1:8765",
    "HOST_AGENT_TOKEN": "test-token",
}
