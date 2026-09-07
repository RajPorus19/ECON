"""Provider capability interface. Concrete providers live in plugins, not core matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ProviderDescriptor:
    name: str
    type: str
    capabilities: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


class CapabilityProvider(Protocol):
    name: str
    provider_type: str

    def capabilities(self) -> list[str]: ...

    def actions(self) -> list[str]: ...

    def descriptor(self) -> ProviderDescriptor: ...
