from rest_framework import serializers

from apps.flows.models import Action, ActionVersion, Flow, FlowEdge, FlowNode
from apps.knowledge.models import Alias, Entity, Intent, IntentAlias, Provider
from apps.llm.models import LlmCall
from apps.plugins.models import Plugin
from apps.requests.models import RequestLog


class IntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intent
        fields = (
            "id",
            "name",
            "description",
            "confidence",
            "usage_count",
            "success_count",
            "failure_count",
            "last_used_at",
            "created_at",
            "updated_at",
        )


class IntentAliasSerializer(serializers.ModelSerializer):
    intent_name = serializers.CharField(source="intent.name", read_only=True)

    class Meta:
        model = IntentAlias
        fields = (
            "id",
            "intent",
            "intent_name",
            "phrase",
            "normalized_phrase",
            "confidence",
            "usage_count",
        )


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = (
            "id",
            "name",
            "type",
            "description",
            "normalized_name",
            "metadata",
            "confidence",
            "usage_count",
            "success_count",
            "failure_count",
            "last_used_at",
            "created_at",
        )


class AliasSerializer(serializers.ModelSerializer):
    entity_name = serializers.CharField(source="entity.name", read_only=True)

    class Meta:
        model = Alias
        fields = (
            "id",
            "entity",
            "entity_name",
            "alias",
            "normalized_alias",
            "confidence",
            "usage_count",
            "last_used_at",
        )


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ("id", "name", "type", "capabilities", "plugin", "created_at")


class ActionVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionVersion
        fields = ("id", "version", "definition", "enabled", "verified", "created_at")


class ActionSerializer(serializers.ModelSerializer):
    versions = ActionVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Action
        fields = (
            "id",
            "name",
            "type",
            "description",
            "executor",
            "parameters_schema",
            "security_level",
            "versions",
        )


class FlowNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowNode
        fields = (
            "id",
            "node_key",
            "node_type",
            "action",
            "entity",
            "provider",
            "position",
            "config",
        )


class FlowEdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowEdge
        fields = ("id", "source_node", "target_node", "condition")


class FlowSerializer(serializers.ModelSerializer):
    nodes = FlowNodeSerializer(many=True, read_only=True)
    edges = FlowEdgeSerializer(many=True, read_only=True)
    intent_name = serializers.CharField(source="intent.name", read_only=True)

    class Meta:
        model = Flow
        fields = (
            "id",
            "name",
            "description",
            "intent",
            "intent_name",
            "version",
            "confidence",
            "usage_count",
            "success_count",
            "failure_count",
            "enabled",
            "nodes",
            "edges",
            "created_at",
            "updated_at",
        )


class FlowWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flow
        fields = ("name", "description", "enabled")


class RequestLogSerializer(serializers.ModelSerializer):
    intent_name = serializers.CharField(source="intent.name", read_only=True)
    entity_name = serializers.CharField(source="entity.name", read_only=True)
    flow_name = serializers.CharField(source="flow.name", read_only=True)

    class Meta:
        model = RequestLog
        fields = (
            "id",
            "created_at",
            "text",
            "normalized_text",
            "intent",
            "intent_name",
            "entity",
            "entity_name",
            "flow",
            "flow_name",
            "llm_used",
            "status",
            "duration_ms",
            "cache_layer",
            "match_method",
            "tokens_saved",
            "estimated_tokens_without_econ",
            "debug",
        )


class LlmCallSerializer(serializers.ModelSerializer):
    request_text = serializers.CharField(source="request.text", read_only=True)

    class Meta:
        model = LlmCall
        fields = (
            "id",
            "created_at",
            "reason",
            "model",
            "prompt",
            "response",
            "prompt_tokens",
            "completion_tokens",
            "duration_ms",
            "success",
            "error",
            "request",
            "request_text",
        )


class PluginSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plugin
        fields = (
            "id",
            "name",
            "version",
            "enabled",
            "capabilities",
            "entity_types",
            "actions",
            "source_path",
            "discovered_at",
        )
