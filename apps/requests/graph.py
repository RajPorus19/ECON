from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.flows.models import Flow
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
