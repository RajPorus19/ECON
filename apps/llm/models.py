from django.db import models

from apps.requests.models import RequestLog


class LlmCall(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    request = models.ForeignKey(
        RequestLog, on_delete=models.SET_NULL, null=True, blank=True, related_name="llm_calls"
    )
    reason = models.CharField(max_length=255)
    model = models.CharField(max_length=128)
    prompt = models.JSONField(default=dict)
    response = models.JSONField(default=dict, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=False)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.created_at:%H:%M:%S} {self.reason}"
