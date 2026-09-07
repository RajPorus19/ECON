from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Project user model. Set AUTH_USER_MODEL before the first migration.

    Source: https://docs.djangoproject.com/en/6.1/topics/auth/customizing/#substituting-a-custom-user-model
    """
