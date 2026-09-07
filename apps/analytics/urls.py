from django.urls import path

from apps.analytics.views import EventStreamView, OptimizationsView, StatsView

urlpatterns = [
    path("stats", StatsView.as_view(), name="api-stats"),
    path("optimizations", OptimizationsView.as_view(), name="api-optimizations"),
    path("events", EventStreamView.as_view(), name="api-events"),
]
