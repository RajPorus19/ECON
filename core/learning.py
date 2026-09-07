"""Pure learning helpers. Alias promotion requires repeated confirmations."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from core.execution import FlowStep
from core.llm import HermesProposal
from core.normalize import normalize

DEFAULT_ALIAS_CONFIRMATIONS = 3
QUERY_TOKEN = "{query}"


@dataclass(frozen=True)
class AliasObservation:
    normalized_phrase: str
    entity_name: str
    confirmations: int


def should_promote_alias(
    confirmations: int, *, required: int = DEFAULT_ALIAS_CONFIRMATIONS
) -> bool:
    """Do not create an alias after a single ambiguous use."""
    return confirmations >= required


def next_confirmation_count(current: int, *, matched_ambiguously: bool, success: bool) -> int:
    if not matched_ambiguously:
        return current
    if success:
        return current + 1
    return max(0, current - 1)


def replacement_phrases(proposal: HermesProposal, _normalized: str = "") -> list[str]:
    """Literal strings that should become {query} in stored steps."""
    found: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        text = raw.strip()
        if len(text) < 2:
            return
        key = text.lower()
        if key in seen:
            return
        seen.add(key)
        found.append(text)
        folded = normalize(text)
        if folded and folded.lower() not in seen:
            seen.add(folded.lower())
            found.append(folded)

    for entity in proposal.entities:
        add(entity.name)
    return found


def strip_trailing_query(normalized: str, query: str) -> str:
    if not normalized or not query:
        return normalized
    folded = normalize(query) or query.lower().strip()
    if not folded:
        return normalized
    if normalized == folded:
        return ""
    suffix = f" {folded}"
    if normalized.endswith(suffix):
        return normalized[: -len(suffix)].strip()
    return normalized


def trigger_phrases(
    *,
    normalized: str,
    query: str = "",
    extra: Sequence[str] = (),
) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        phrase = normalize(raw) if raw else ""
        if not phrase or phrase in seen:
            return
        seen.add(phrase)
        found.append(phrase)

    if normalized:
        add(normalized)
        prefix = strip_trailing_query(normalized, query)
        if prefix:
            add(prefix)
        parts = normalized.split()
        if len(parts) > 1:
            add(parts[0])
    for item in extra:
        add(item)
    return found


def template_text(value: str, replacements: Sequence[str]) -> str:
    rendered = value
    phrases = sorted(
        {phrase for phrase in replacements if phrase and len(phrase) >= 2},
        key=len,
        reverse=True,
    )
    for phrase in phrases:
        rendered = re.compile(re.escape(phrase), re.IGNORECASE).sub(QUERY_TOKEN, rendered)
    return rendered


def template_value(value: Any, replacements: Sequence[str]) -> Any:
    if isinstance(value, str):
        return template_text(value, replacements)
    if isinstance(value, dict):
        return {str(key): template_value(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [template_value(item, replacements) for item in value]
    return value


def template_steps(steps: list[FlowStep], replacements: Sequence[str]) -> list[FlowStep]:
    templated: list[FlowStep] = []
    for step in steps:
        templated.append(
            FlowStep(
                executor=step.executor,
                argv=[template_text(part, replacements) for part in step.argv],
                extra=template_value(step.extra, replacements) if step.extra else {},
                security_level=step.security_level,
            )
        )
    return templated


def steps_signature(steps: list[FlowStep]) -> tuple:
    packed = []
    for step in steps:
        packed.append(
            (
                (step.executor or "shell").lower(),
                tuple(step.argv),
                json.dumps(step.extra or {}, sort_keys=True, default=str),
            )
        )
    return tuple(packed)


def contains_query_token(steps: list[FlowStep]) -> bool:
    for step in steps:
        if any(QUERY_TOKEN in part for part in step.argv):
            return True
        if QUERY_TOKEN in json.dumps(step.extra or {}):
            return True
    return False
