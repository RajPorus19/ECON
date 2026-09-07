from django.contrib import admin

from .models import DailyMetric


@admin.register(DailyMetric)
class DailyMetricAdmin(admin.ModelAdmin):
    list_display = (
        "day",
        "requests_total",
        "llm_calls_total",
        "execution_success_total",
        "execution_failure_total",
    )
