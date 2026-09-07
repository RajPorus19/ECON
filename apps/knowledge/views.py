from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.knowledge.models import Alias, Entity, Intent, IntentAlias, Provider
from apps.knowledge.serializers import (
    AliasSerializer,
    EntitySerializer,
    IntentAliasSerializer,
    IntentSerializer,
    PluginSerializer,
    ProviderSerializer,
)
from apps.plugins.models import Plugin
from apps.plugins.registry import discover_and_sync


class IntentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = Intent.objects.all().order_by("name")
    serializer_class = IntentSerializer


class IntentAliasViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = IntentAlias.objects.select_related("intent").all()
    serializer_class = IntentAliasSerializer


class EntityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = Entity.objects.all().order_by("-usage_count", "name")
    serializer_class = EntitySerializer


class AliasViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = Alias.objects.select_related("entity").all()
    serializer_class = AliasSerializer


class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = Provider.objects.all().order_by("name")
    serializer_class = ProviderSerializer


class PluginViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    queryset = Plugin.objects.all().order_by("name")
    serializer_class = PluginSerializer

    @action(detail=False, methods=["post"])
    def discover(self, _request):
        synced = discover_and_sync()
        return Response({"discovered": [plugin.name for plugin in synced]})
