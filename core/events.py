"""In-process event bus. No broker required on the execute hot path."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

Listener = Callable[[str, dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)

    def subscribe(self, event: str, listener: Listener) -> None:
        self._listeners[event].append(listener)

    def emit(self, event: str, payload: dict[str, Any] | None = None) -> None:
        data = payload or {}
        for listener in self._listeners.get(event, []):
            listener(event, data)
        for listener in self._listeners.get("*", []):
            listener(event, data)


REQUEST_RECEIVED = "request.received"
REQUEST_MATCHED = "request.matched"
LLM_CALLED = "llm.called"
KNOWLEDGE_CREATED = "knowledge.created"
FLOW_CREATED = "flow.created"
EXECUTION_STARTED = "execution.started"
EXECUTION_COMPLETED = "execution.completed"
EXECUTION_FAILED = "execution.failed"
EXECUTION_DENIED = "execution.denied"
