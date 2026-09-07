from rest_framework import routers

from apps.flows.views import ActionViewSet, FlowViewSet

router = routers.DefaultRouter(trailing_slash=False)
router.register("flows", FlowViewSet)
router.register("actions", ActionViewSet)

urlpatterns = router.urls
