from django.urls import path

from apps.requests.views import ExecuteView, HealthView

urlpatterns = [
    path("health", HealthView.as_view(), name="api-health"),
    path("execute", ExecuteView.as_view(), name="api-execute"),
]
