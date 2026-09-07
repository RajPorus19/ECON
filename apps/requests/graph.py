from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.flows.models import Action, Flow
from apps.knowledge.models import Entity, Intent, Provider
from apps.knowledge.serializers import RequestLogSerializer
from apps.requests.models import RequestLog


class RequestLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = RequestLog.objects.select_related("intent", "entity", "flow").all()
    serializer_class = RequestLogSerializer


class GraphView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        query = (request.query_params.get("q") or "").strip().lower()
        nodes: list[dict] = []
        edges: list[dict] = []

        intents = Intent.objects.all()
        entities = Entity.objects.all()
        providers = Provider.objects.all()
        flows = Flow.objects.filter(enabled=True).prefetch_related("nodes")
        if query:
            intents = intents.filter(name__icontains=query)
            entities = entities.filter(name__icontains=query)
            providers = providers.filter(name__icontains=query)
            flows = flows.filter(name__icontains=query)

        for intent in intents:
            nodes.append(
                {
                    "id": f"intent:{intent.pk}",
                    "type": "intent",
                    "label": intent.name,
                    "confidence": intent.confidence,
                    "usage": intent.usage_count,
                    "aliases": list(intent.aliases.values_list("phrase", flat=True)[:20]),
                    "connected_flows": [f.name for f in intent.flows.filter(enabled=True)[:10]],
                    "last_execution": _last_execution(intent_id=intent.pk),
                }
            )
        for entity in entities:
            nodes.append(
                {
                    "id": f"entity:{entity.pk}",
                    "type": "entity",
                    "label": entity.name,
                    "confidence": entity.confidence,
                    "usage": entity.usage_count,
                    "entity_type": entity.type,
                    "aliases": list(entity.aliases.values_list("alias", flat=True)[:20]),
                    "connected_flows": [
                        node.flow.name
                        for node in entity.flow_nodes.select_related("flow")[:10]
                        if node.flow_id
                    ],
                    "last_execution": _last_execution(entity_id=entity.pk),
                }
            )
        for provider in providers:
            nodes.append(
                {
                    "id": f"provider:{provider.pk}",
                    "type": "provider",
                    "label": provider.name,
                    "capabilities": provider.capabilities,
                }
            )
        for flow in flows:
            nodes.append(
                {
                    "id": f"flow:{flow.pk}",
                    "type": "flow",
                    "label": f"{flow.name} v{flow.version}",
                    "confidence": flow.confidence,
                    "usage": flow.usage_count,
                    "success": flow.success_count,
                    "failure": flow.failure_count,
                    "aliases": [],
                    "connected_flows": [flow.name],
                    "last_execution": _last_execution(flow_id=flow.pk),
                }
            )
            if flow.intent_id:
                edges.append(
                    {
                        "source": f"intent:{flow.intent_id}",
                        "target": f"flow:{flow.pk}",
                    }
                )
            for node in flow.nodes.all():
                if node.entity_id:
                    edges.append(
                        {
                            "source": f"flow:{flow.pk}",
                            "target": f"entity:{node.entity_id}",
                        }
                    )
                if node.provider_id:
                    edges.append(
                        {
                            "source": f"entity:{node.entity_id}"
                            if node.entity_id
                            else f"flow:{flow.pk}",
                            "target": f"provider:{node.provider_id}",
                        }
                    )
                if node.action_id:
                    action_id = f"action:{node.action_id}"
                    if not any(item["id"] == action_id for item in nodes):
                        nodes.append(
                            {
                                "id": action_id,
                                "type": "action",
                                "label": node.action.name if node.action else "action",
                            }
                        )
                    edges.append({"source": f"flow:{flow.pk}", "target": action_id})
        return Response({"nodes": nodes, "edges": edges})


class GraphDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        node_id = (request.query_params.get("id") or "").strip()
        detail = node_detail(node_id)
        if detail is None:
            return Response({"detail": "not found"}, status=404)
        return Response(detail)


def _last_execution(
    *, intent_id: int | None = None, entity_id: int | None = None, flow_id: int | None = None
) -> dict | None:
    qs = RequestLog.objects.order_by("-created_at")
    if intent_id is not None:
        qs = qs.filter(intent_id=intent_id)
    if entity_id is not None:
        qs = qs.filter(entity_id=entity_id)
    if flow_id is not None:
        qs = qs.filter(flow_id=flow_id)
    log = qs.first()
    if log is None:
        return None
    return {
        "id": log.pk,
        "text": log.text,
        "status": log.status,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def node_detail(node_id: str) -> dict | None:
    kind, _, raw = node_id.partition(":")
    if not raw.isdigit():
        return None
    pk = int(raw)
    if kind == "intent":
        intent = Intent.objects.filter(pk=pk).first()
        if intent is None:
            return None
        return {
            "id": node_id,
            "name": intent.name,
            "type": "intent",
            "confidence": intent.confidence,
            "usage": intent.usage_count,
            "aliases": list(intent.aliases.values_list("phrase", flat=True)),
            "connected_flows": list(intent.flows.values_list("name", flat=True)),
            "last_execution": _last_execution(intent_id=intent.pk),
        }
    if kind == "entity":
        entity = Entity.objects.filter(pk=pk).first()
        if entity is None:
            return None
        return {
            "id": node_id,
            "name": entity.name,
            "type": "entity",
            "confidence": entity.confidence,
            "usage": entity.usage_count,
            "aliases": list(entity.aliases.values_list("alias", flat=True)),
            "connected_flows": list(
                Flow.objects.filter(nodes__entity=entity).values_list("name", flat=True).distinct()
            ),
            "last_execution": _last_execution(entity_id=entity.pk),
        }
    if kind == "flow":
        flow = Flow.objects.filter(pk=pk).first()
        if flow is None:
            return None
        return {
            "id": node_id,
            "name": flow.name,
            "type": "flow",
            "confidence": flow.confidence,
            "usage": flow.usage_count,
            "aliases": [],
            "connected_flows": [flow.name],
            "last_execution": _last_execution(flow_id=flow.pk),
        }
    if kind == "provider":
        provider = Provider.objects.filter(pk=pk).first()
        if provider is None:
            return None
        return {
            "id": node_id,
            "name": provider.name,
            "type": "provider",
            "confidence": 1.0,
            "usage": 0,
            "aliases": [],
            "connected_flows": list(
                Flow.objects.filter(nodes__provider=provider)
                .values_list("name", flat=True)
                .distinct()
            ),
            "last_execution": None,
        }
    if kind == "action":
        action = Action.objects.filter(pk=pk).first()
        if action is None:
            return None
        return {
            "id": node_id,
            "name": action.name,
            "type": "action",
            "confidence": 1.0,
            "usage": 0,
            "aliases": [],
            "connected_flows": list(
                Flow.objects.filter(nodes__action=action).values_list("name", flat=True).distinct()
            ),
            "last_execution": None,
        }
    return None
