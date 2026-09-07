from rest_framework import routers

from apps.knowledge.views import (
    AliasViewSet,
    EntityViewSet,
    IntentAliasViewSet,
    IntentViewSet,
    PluginViewSet,
    ProviderViewSet,
)

router = routers.DefaultRouter(trailing_slash=False)
router.register("intents", IntentViewSet)
router.register("intent-aliases", IntentAliasViewSet)
router.register("entities", EntityViewSet)
router.register("aliases", AliasViewSet)
router.register("providers", ProviderViewSet)
router.register("plugins", PluginViewSet)

urlpatterns = router.urls
