from django.core.management.base import BaseCommand

from apps.flows.models import Action, ActionVersion
from apps.knowledge.models import Intent, IntentAlias
from core.normalize import normalize

LAUNCH_PHRASES = ("lance", "lancer", "start", "run", "open", "ouvre", "demarre", "démarre")
DEFAULT_INTENTS = (
    ("launch_program", "Launch an application or game", LAUNCH_PHRASES),
    ("shell_execute", "Run a shell command", ("execute", "exec", "shell")),
    ("play_media", "Play media on a provider", ("play", "mets", "watch")),
)


class Command(BaseCommand):
    help = "Seed default intents, aliases, and the shell.execute action."

    def handle(self, *args, **options) -> None:
        for name, description, phrases in DEFAULT_INTENTS:
            intent, created = Intent.objects.get_or_create(
                name=name,
                defaults={"description": description, "confidence": 1.0},
            )
            self.stdout.write(f"{'Created' if created else 'Exists'} intent {intent.name}")
            for phrase in phrases:
                IntentAlias.objects.get_or_create(
                    normalized_phrase=normalize(phrase),
                    defaults={
                        "intent": intent,
                        "phrase": phrase,
                        "confidence": 1.0,
                    },
                )

        action, created = Action.objects.get_or_create(
            name="shell.execute",
            defaults={
                "type": "shell",
                "description": "Execute an argv list on the host",
                "executor": "shell",
                "security_level": 1,
            },
        )
        if created or not action.versions.exists():
            ActionVersion.objects.get_or_create(
                action=action,
                version=1,
                defaults={
                    "definition": {"executor": "shell", "argv": ["echo", "ok"]},
                    "enabled": True,
                    "verified": True,
                },
            )
            self.stdout.write("Created action shell.execute v1")
        from apps.plugins.registry import discover_and_sync

        for plugin in discover_and_sync():
            self.stdout.write(f"Plugin {plugin.name} {plugin.version}")
        self.stdout.write(self.style.SUCCESS("Seed complete."))
