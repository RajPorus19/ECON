from django.db import models

from apps.execution.models import ExecutionAudit
from apps.flows.models import Flow
from apps.knowledge.models import Entity, Intent


class RequestLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    normalized_text = models.CharField(max_length=512, blank=True)
    intent = models.ForeignKey(
        Intent, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests"
    )
    entity = models.ForeignKey(
        Entity, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests"
    )
    flow = models.ForeignKey(
        Flow, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests"
    )
    llm_used = models.BooleanField(default=False)
    status = models.CharField(max_length=32)
    execution = models.ForeignKey(
        ExecutionAudit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="request_logs",
    )
    duration_ms = models.PositiveIntegerField(default=0)
    debug = models.JSONField(default=dict, blank=True)
    proposal = models.JSONField(default=dict, blank=True)
    cache_layer = models.CharField(max_length=8, blank=True)
    match_method = models.CharField(max_length=32, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    estimated_tokens_without_econ = models.PositiveIntegerField(default=0)
    tokens_saved = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.created_at:%H:%M:%S} {self.text[:40]}"
