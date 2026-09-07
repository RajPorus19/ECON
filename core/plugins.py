"""Plugin manifests. Core stays unaware of Steam/Jellyfin specifics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PluginAction:
    id: str
    executor: str = "shell"
    parameters: dict[str, Any] = field(default_factory=dict)
    command: list[str] = field(default_factory=list)
    security_level: int = 1


@dataclass
class PluginManifest:
    name: str
    version: str = "0.1.0"
    entity_types: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    actions: list[PluginAction] = field(default_factory=list)
    path: str = ""

    def action_ids(self) -> list[str]:
        return [action.id for action in self.actions]


def _parse_action(raw: Any) -> PluginAction:
    if isinstance(raw, str):
        return PluginAction(id=raw)
    if not isinstance(raw, dict) or not raw.get("id"):
        raise ValueError("plugin action must have an id")
    command = raw.get("command") or []
    if isinstance(command, str):
        command = [command]
    return PluginAction(
        id=str(raw["id"]),
        executor=str(raw.get("executor") or "shell"),
        parameters=dict(raw.get("parameters") or {}),
        command=[str(part) for part in command],
        security_level=int(raw.get("security_level") or 1),
    )


def load_manifest(path: Path) -> PluginManifest:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not data.get("name"):
        raise ValueError(f"plugin manifest missing name: {path}")
    actions = [_parse_action(item) for item in data.get("actions") or []]
    entity_types = list(data.get("entity_types") or data.get("entities") or [])
    return PluginManifest(
        name=str(data["name"]),
        version=str(data.get("version") or "0.1.0"),
        entity_types=[str(item) for item in entity_types],
        capabilities=[str(item) for item in data.get("capabilities") or []],
        actions=actions,
        path=str(path),
    )


def discover_manifests(root: Path) -> list[PluginManifest]:
    manifests: list[PluginManifest] = []
    if not root.exists():
        return manifests
    for yaml_path in sorted(root.glob("*/plugin.yaml")):
        manifests.append(load_manifest(yaml_path))
    return manifests
