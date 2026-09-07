from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok", "service": "econ"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health),
    path("api/v1/", include("apps.requests.urls")),
    path("api/v1/", include("apps.knowledge.urls")),
    path("api/v1/", include("apps.flows.urls")),
    path("api/v1/", include("apps.analytics.urls")),
]
