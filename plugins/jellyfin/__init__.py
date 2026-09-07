"""Jellyfin provider plugin. Credentials come from env, never from flows or prompts."""

from core.providers import ProviderDescriptor


class JellyfinProvider:
    name = "Jellyfin"
    provider_type = "media_server"

    def capabilities(self) -> list[str]:
        return ["search", "play", "pause", "stop"]

    def actions(self) -> list[str]:
        return ["jellyfin.search", "jellyfin.play", "jellyfin.pause", "jellyfin.stop"]

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            name=self.name,
            type=self.provider_type,
            capabilities=self.capabilities(),
            actions=self.actions(),
            config={"url_env": "JELLYFIN_URL", "api_key_env": "JELLYFIN_API_KEY"},
        )
