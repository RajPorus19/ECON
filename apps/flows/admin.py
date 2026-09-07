from django.contrib import admin

from .models import Action, ActionVersion, Flow, FlowEdge, FlowNode


class ActionVersionInline(admin.TabularInline):
    model = ActionVersion
    extra = 0


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "executor", "security_level")
    list_filter = ("executor", "security_level")
    search_fields = ("name",)
    inlines = [ActionVersionInline]


@admin.register(ActionVersion)
class ActionVersionAdmin(admin.ModelAdmin):
    list_display = ("action", "version", "enabled", "verified")
    list_filter = ("enabled", "verified")


class FlowNodeInline(admin.TabularInline):
    model = FlowNode
    extra = 0


class FlowEdgeInline(admin.TabularInline):
    model = FlowEdge
    extra = 0
    fk_name = "flow"


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "intent",
        "version",
        "confidence",
        "usage_count",
        "success_count",
        "enabled",
    )
    list_filter = ("enabled",)
    search_fields = ("name",)
    inlines = [FlowNodeInline, FlowEdgeInline]


@admin.register(FlowNode)
class FlowNodeAdmin(admin.ModelAdmin):
    list_display = ("flow", "node_key", "node_type", "action", "entity", "position")


@admin.register(FlowEdge)
class FlowEdgeAdmin(admin.ModelAdmin):
    list_display = ("flow", "source_node", "target_node")
