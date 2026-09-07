"""Discover plugin YAML manifests and sync the Django registry."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.flows.models import Action, ActionVersion
from apps.knowledge.models import Provider
from apps.plugins.models import Plugin
from core.plugins import PluginManifest, discover_manifests


def plugin_root() -> Path:
    configured = getattr(settings, "ECON", {}).get("PLUGIN_ROOT")
    if configured:
        return Path(str(configured))
    return Path(settings.BASE_DIR) / "plugins"


def discover_and_sync() -> list[Plugin]:
    manifests = discover_manifests(plugin_root())
    synced: list[Plugin] = []
    now = timezone.now()
    for manifest in manifests:
        plugin, _ = Plugin.objects.update_or_create(
            name=manifest.name,
            defaults={
                "version": manifest.version,
                "capabilities": manifest.capabilities,
                "entity_types": manifest.entity_types,
                "actions": manifest.action_ids(),
                "source_path": manifest.path,
                "discovered_at": now,
                "enabled": True,
            },
        )
        Provider.objects.update_or_create(
            name=manifest.name.title() if manifest.name.islower() else manifest.name,
            defaults={
                "type": "plugin",
                "capabilities": manifest.capabilities,
                "plugin": manifest.name,
                "config": {"env_refs": True},
            },
        )
        _ensure_actions(manifest)
        synced.append(plugin)
    return synced


def _ensure_actions(manifest: PluginManifest) -> None:
    for item in manifest.actions:
        action, _ = Action.objects.get_or_create(
            name=item.id,
            defaults={
                "type": item.executor,
                "executor": item.executor,
                "parameters_schema": item.parameters,
                "security_level": item.security_level,
                "description": f"{manifest.name} action",
            },
        )
        if not action.versions.exists():
            ActionVersion.objects.create(
                action=action,
                version=1,
                definition={
                    "executor": item.executor,
                    "command": item.command,
                    "parameters": item.parameters,
                },
                enabled=True,
                verified=True,
            )
