from django.contrib import admin

from .models import RequestLog


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "text",
        "intent",
        "entity",
        "llm_used",
        "status",
        "duration_ms",
    )
    list_filter = ("llm_used", "status")
    search_fields = ("text", "normalized_text")
    readonly_fields = (
        "created_at",
        "text",
        "normalized_text",
        "intent",
        "entity",
        "flow",
        "llm_used",
        "status",
        "execution",
        "duration_ms",
        "debug",
    )
