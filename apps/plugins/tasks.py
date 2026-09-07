from celery import shared_task

from apps.plugins.registry import discover_and_sync


@shared_task
def discover_plugins() -> list[str]:
    return [plugin.name for plugin in discover_and_sync()]
