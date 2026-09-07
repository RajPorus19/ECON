from django.core.management.base import BaseCommand

from apps.plugins.registry import discover_and_sync


class Command(BaseCommand):
    help = "Discover plugin YAML manifests and sync the registry."

    def handle(self, *args, **options) -> None:
        plugins = discover_and_sync()
        for plugin in plugins:
            self.stdout.write(f"{plugin.name} {plugin.version} ({', '.join(plugin.capabilities)})")
        self.stdout.write(self.style.SUCCESS(f"Synced {len(plugins)} plugin(s)."))
