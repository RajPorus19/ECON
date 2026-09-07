from django.conf import settings
from django.db import models

from apps.flows.models import Action, Flow
from apps.knowledge.models import Entity, Intent


class ExecutionStatus(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    DENIED = "denied", "Denied"
    CONFIRM_REQUIRED = "confirm_required", "Confirm required"
    SKIPPED = "skipped", "Skipped"


class ExecutionAudit(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="execution_audits",
    )
    request_text = models.TextField(blank=True)
    flow = models.ForeignKey(
        Flow, on_delete=models.SET_NULL, null=True, blank=True, related_name="audits"
    )
    intent = models.ForeignKey(
        Intent, on_delete=models.SET_NULL, null=True, blank=True, related_name="audits"
    )
    entity = models.ForeignKey(
        Entity, on_delete=models.SET_NULL, null=True, blank=True, related_name="audits"
    )
    action = models.ForeignKey(
        Action, on_delete=models.SET_NULL, null=True, blank=True, related_name="audits"
    )
    argv = models.JSONField(default=list, blank=True)
    security_decision = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=32, choices=ExecutionStatus.choices)
    result = models.JSONField(default=dict, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.status}"
