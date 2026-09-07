from django.contrib import admin

from .models import ExecutionAudit


@admin.register(ExecutionAudit)
class ExecutionAuditAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "status",
        "security_decision",
        "intent",
        "entity",
        "action",
        "duration_ms",
    )
    list_filter = ("status", "security_decision")
    search_fields = ("request_text",)
    readonly_fields = (
        "created_at",
        "actor",
        "request_text",
        "flow",
        "intent",
        "entity",
        "action",
        "argv",
        "security_decision",
        "status",
        "result",
        "duration_ms",
    )
