from django.db import models

from apps.mixins import TimeStampedModel


class EntityType(models.TextChoices):
    APPLICATION = "application", "Application"
    GAME = "game", "Game"
    MOVIE = "movie", "Movie"
    TV_SHOW = "tv_show", "TV show"
    MUSIC = "music", "Music"
    WEBSITE = "website", "Website"
    PERSON = "person", "Person"
    DEVICE = "device", "Device"
    SERVICE = "service", "Service"
    FILE = "file", "File"
    FOLDER = "folder", "Folder"


class Entity(TimeStampedModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=EntityType.choices)
    description = models.TextField(blank=True)
    normalized_name = models.CharField(max_length=255, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(default=0.5)
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "entities"
        indexes = [
            models.Index(fields=["normalized_name", "type"]),
        ]

    def __str__(self) -> str:
        return self.name


class Alias(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=255)
    normalized_alias = models.CharField(max_length=255, db_index=True)
    confidence = models.FloatField(default=0.5)
    usage_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "aliases"
        constraints = [
            models.UniqueConstraint(
                fields=["entity", "normalized_alias"],
                name="uniq_alias_per_entity",
            )
        ]

    def __str__(self) -> str:
        return f"{self.alias} → {self.entity}"


class Intent(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True)
    confidence = models.FloatField(default=1.0)
    usage_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.name


class IntentAlias(models.Model):
    intent = models.ForeignKey(Intent, on_delete=models.CASCADE, related_name="aliases")
    phrase = models.CharField(max_length=255)
    normalized_phrase = models.CharField(max_length=255, db_index=True)
    confidence = models.FloatField(default=1.0)

    class Meta:
        verbose_name_plural = "intent aliases"
        constraints = [
            models.UniqueConstraint(fields=["normalized_phrase"], name="uniq_intent_alias_phrase")
        ]

    def __str__(self) -> str:
        return f"{self.phrase} → {self.intent}"


class Provider(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)
    type = models.CharField(max_length=64)
    config = models.JSONField(default=dict, blank=True)
    capabilities = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return self.name
