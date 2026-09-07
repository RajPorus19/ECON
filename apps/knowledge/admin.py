from django.contrib import admin

from .models import Alias, Entity, Intent, IntentAlias, Provider


class AliasInline(admin.TabularInline):
    model = Alias
    extra = 0


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "confidence", "usage_count", "last_used_at")
    list_filter = ("type",)
    search_fields = ("name", "normalized_name")
    inlines = [AliasInline]


@admin.register(Alias)
class AliasAdmin(admin.ModelAdmin):
    list_display = ("alias", "entity", "confidence", "usage_count")
    search_fields = ("alias", "normalized_alias")


class IntentAliasInline(admin.TabularInline):
    model = IntentAlias
    extra = 0


@admin.register(Intent)
class IntentAdmin(admin.ModelAdmin):
    list_display = ("name", "confidence", "usage_count")
    search_fields = ("name",)
    inlines = [IntentAliasInline]


@admin.register(IntentAlias)
class IntentAliasAdmin(admin.ModelAdmin):
    list_display = ("phrase", "intent", "confidence")
    search_fields = ("phrase", "normalized_phrase")


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "type")
    search_fields = ("name",)
