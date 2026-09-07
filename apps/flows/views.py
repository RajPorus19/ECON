from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.flows.models import Action, Flow
from apps.knowledge.learning import apply_graph_version, clone_flow_version
from apps.knowledge.serializers import ActionSerializer, FlowSerializer, FlowWriteSerializer
from apps.requests.runtime import get_phrase_cache
from apps.requests.services import build_executor
from core.execution import ExecuteRequest
from core.security import evaluate


class FlowViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = Flow.objects.all().prefetch_related("nodes", "edges").order_by("-updated_at")
    serializer_class = FlowSerializer

    def get_serializer_class(self):
        if self.action in {"partial_update", "update"}:
            return FlowWriteSerializer
        return FlowSerializer

    def update(self, request, *args, **kwargs):
        flow = self.get_object()
        data = request.data if isinstance(request.data, dict) else {}
        if "nodes" in data or "edges" in data:
            clone = apply_graph_version(flow, data)
            get_phrase_cache().invalidate_flow(str(flow.pk))
            get_phrase_cache().invalidate_flow(str(clone.pk))
            return Response(FlowSerializer(clone).data)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def disable(self, _request, pk=None):
        flow = self.get_object()
        flow.enabled = False
        flow.save(update_fields=["enabled"])
        get_phrase_cache().invalidate_flow(str(flow.pk))
        return Response(FlowSerializer(flow).data)

    @action(detail=True, methods=["post"])
    def version(self, _request, pk=None):
        flow = self.get_object()
        clone = clone_flow_version(flow, enabled=True)
        flow.enabled = False
        flow.save(update_fields=["enabled"])
        get_phrase_cache().invalidate_flow(str(flow.pk))
        return Response(FlowSerializer(clone).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        flow = self.get_object()
        node = flow.nodes.filter(action__isnull=False).order_by("position").first()
        argv = []
        if node and isinstance(node.config.get("argv"), list):
            argv = [str(part) for part in node.config["argv"]]
        confirmed = bool(request.data.get("confirm")) if isinstance(request.data, dict) else False
        verdict = evaluate(argv, confirmed=confirmed)
        if str(verdict.decision) != "auto":
            return Response(
                {"status": str(verdict.decision), "reason": verdict.reason, "argv": argv},
                status=202 if str(verdict.decision) == "confirm" else 403,
            )
        result = build_executor().execute(ExecuteRequest(argv=argv))
        return Response(
            {
                "status": "success" if result.success else "failed",
                "argv": argv,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.error,
            }
        )


class ActionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = Action.objects.all().prefetch_related("versions").order_by("name")
    serializer_class = ActionSerializer
