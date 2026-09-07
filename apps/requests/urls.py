from django.urls import path
from rest_framework import routers, viewsets
from rest_framework.permissions import AllowAny

from apps.knowledge.serializers import LlmCallSerializer
from apps.llm.models import LlmCall
from apps.requests.graph import GraphView, RequestLogViewSet
from apps.requests.views import ExecuteView, HealthView


class LlmCallViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = LlmCall.objects.select_related("request").all()
    serializer_class = LlmCallSerializer


router = routers.DefaultRouter(trailing_slash=False)
router.register("requests", RequestLogViewSet)
router.register("llm-calls", LlmCallViewSet)

urlpatterns = [
    path("health", HealthView.as_view(), name="api-health"),
    path("execute", ExecuteView.as_view(), name="api-execute"),
    path("graph", GraphView.as_view(), name="api-graph"),
    *router.urls,
]
