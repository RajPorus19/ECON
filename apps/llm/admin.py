from django.contrib import admin

from .models import LlmCall


@admin.register(LlmCall)
class LlmCallAdmin(admin.ModelAdmin):
    list_display = ("created_at", "reason", "model", "success", "prompt_tokens", "duration_ms")
    list_filter = ("success", "model")
    readonly_fields = (
        "created_at",
        "request",
        "reason",
        "model",
        "prompt",
        "response",
        "prompt_tokens",
        "completion_tokens",
        "duration_ms",
        "success",
        "error",
    )
