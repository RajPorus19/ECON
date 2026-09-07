from django.db import models


class Plugin(models.Model):
    """Registry stub. Concrete plugins land in a later phase."""

    name = models.CharField(max_length=128, unique=True)
    version = models.CharField(max_length=32, default="0.0.0")
    enabled = models.BooleanField(default=False)
    capabilities = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
