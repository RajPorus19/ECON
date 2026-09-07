from django.contrib import admin

from .models import Plugin


@admin.register(Plugin)
class PluginAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "enabled")
    list_filter = ("enabled",)
