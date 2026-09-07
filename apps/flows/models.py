from django.db import models

from apps.knowledge.models import Entity, Intent, Provider
from apps.mixins import TimeStampedModel


class Action(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)
    type = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    executor = models.CharField(max_length=64, default="shell")
    parameters_schema = models.JSONField(default=dict, blank=True)
    security_level = models.PositiveSmallIntegerField(default=1)

    def __str__(self) -> str:
        return self.name


class ActionVersion(models.Model):
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    definition = models.JSONField(default=dict)
    enabled = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["action", "version"], name="uniq_action_version"),
        ]
        ordering = ["-version"]

    def __str__(self) -> str:
        return f"{self.action.name} v{self.version}"


class Flow(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    intent = models.ForeignKey(
        Intent, on_delete=models.SET_NULL, null=True, blank=True, related_name="flows"
    )
    version = models.PositiveIntegerField(default=1)
    confidence = models.FloatField(default=0.5)
    usage_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name", "version"], name="uniq_flow_version"),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class FlowNode(models.Model):
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name="nodes")
    node_key = models.CharField(max_length=64)
    node_type = models.CharField(max_length=64)
    action = models.ForeignKey(
        Action, on_delete=models.SET_NULL, null=True, blank=True, related_name="flow_nodes"
    )
    entity = models.ForeignKey(
        Entity, on_delete=models.SET_NULL, null=True, blank=True, related_name="flow_nodes"
    )
    provider = models.ForeignKey(
        Provider, on_delete=models.SET_NULL, null=True, blank=True, related_name="flow_nodes"
    )
    position = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["flow", "node_key"], name="uniq_flow_node_key"),
        ]

    def __str__(self) -> str:
        return f"{self.flow.name}:{self.node_key}"


class FlowEdge(models.Model):
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name="edges")
    source_node = models.ForeignKey(
        FlowNode, on_delete=models.CASCADE, related_name="outgoing_edges"
    )
    target_node = models.ForeignKey(
        FlowNode, on_delete=models.CASCADE, related_name="incoming_edges"
    )
    condition = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"{self.source_node.node_key} → {self.target_node.node_key}"
