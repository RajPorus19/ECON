"""Steam provider plugin. Declares game launch capability; no secrets in manifests."""

from core.providers import ProviderDescriptor


class SteamProvider:
    name = "Steam"
    provider_type = "game_store"

    def capabilities(self) -> list[str]:
        return ["launch"]

    def actions(self) -> list[str]:
        return ["steam.launch"]

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            name=self.name,
            type=self.provider_type,
            capabilities=self.capabilities(),
            actions=self.actions(),
        )
