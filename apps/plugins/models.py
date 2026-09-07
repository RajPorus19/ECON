from django.db import models


class Plugin(models.Model):
    name = models.CharField(max_length=128, unique=True)
    version = models.CharField(max_length=32, default="0.1.0")
    enabled = models.BooleanField(default=True)
    capabilities = models.JSONField(default=list, blank=True)
    entity_types = models.JSONField(default=list, blank=True)
    actions = models.JSONField(default=list, blank=True)
    permissions = models.JSONField(default=dict, blank=True)
    config = models.JSONField(default=dict, blank=True)
    source_path = models.CharField(max_length=512, blank=True)
    discovered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
