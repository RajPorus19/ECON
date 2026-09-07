"""Runtime pipeline: cache → match → (Hermes) → validate → execute.

Learning and cache writes happen off the hot path via callers/Celery.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from core import events
from core.cache import CachedResolution, PhraseCache, lookup_layers
from core.compiler import CompileError, compile_proposal
from core.confidence import combined_confidence, meets_threshold
from core.embeddings import EmbeddingBackend, NullEmbeddingBackend
from core.events import EventBus
from core.execution import (
    ExecuteRequest,
    ExecuteResult,
    Executor,
    FlowStep,
    flatten_argv,
    normalize_steps,
)
from core.execution.http import interpolate_command, interpolate_mapping, json_bindings
from core.execution.registry import executor_for
from core.learning import contains_query_token
from core.llm import HermesProposal, LLMProvider
from core.matching import longest_prefix_match, match_entity
from core.normalize import normalize, original_span
from core.secrets import redact_mapping
from core.security import Decision, SecurityLevel, SecurityPolicy, SecurityVerdict, evaluate
from core.tokens import DEFAULT_ESTIMATED_BASELINE, estimated_tokens_saved


@dataclass
class MatchSnapshot:
    intent_name: str | None = None
    intent_confidence: float = 0.0
    entity_name: str | None = None
    entity_confidence: float = 0.0
    provider_name: str | None = None
    provider_confidence: float = 0.0
    flow_id: str | None = None
    flow_confidence: float = 0.0
    combined: float = 0.0
    known: bool = False
    method: str = ""
    ambiguous_entity: bool = False
    query: str = ""


@dataclass
class PipelineResult:
    status: str
    intent: str | None
    entity: str | None
    flow_id: str | None
    execution_time_ms: int
    llm_used: bool
    argv: list[str] = field(default_factory=list)
    message: str = ""
    security_decision: str = ""
    execution: ExecuteResult | None = None
    debug: dict[str, Any] = field(default_factory=dict)
    proposal: HermesProposal | None = None
    cache_layer: str = ""
    combined_confidence: float = 0.0
    match_method: str = ""
    provider: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_tokens_without_econ: int = 0
    tokens_saved: int = 0
    original_text: str = ""
    normalized_text: str = ""
    ambiguous_entity: bool = False
    steps: list[dict[str, Any]] = field(default_factory=list)


class KnowledgeSource(Protocol):
    def intent_aliases(self) -> list[tuple[str, str, float]]: ...

    def entity_names(self) -> list[tuple[str, str, float]]: ...

    def find_flow(
        self, intent_name: str, entity_name: str | None
    ) -> tuple[str, float, list[str] | list[dict[str, Any]]] | None:
        """Return (flow_id, confidence, argv or step dicts) if a known flow exists."""
        ...


class Pipeline:
    def __init__(
        self,
        *,
        knowledge: KnowledgeSource,
        executor: Executor,
        llm: LLMProvider | None,
        bus: EventBus | None = None,
        cache: PhraseCache | None = None,
        embedder: EmbeddingBackend | None = None,
        confidence_threshold: float = 0.90,
        semantic_threshold: float = 0.82,
        timeout_s: float = 30.0,
        security_policy: SecurityPolicy | None = None,
        estimated_baseline_tokens: int = DEFAULT_ESTIMATED_BASELINE,
    ) -> None:
        self.knowledge = knowledge
        self.executor = executor
        self.llm = llm
        self.bus = bus or EventBus()
        self.cache = cache
        self.embedder = embedder or NullEmbeddingBackend()
        self.confidence_threshold = confidence_threshold
        self.semantic_threshold = semantic_threshold
        self.timeout_s = timeout_s
        self.security_policy = security_policy or SecurityPolicy()
        self.estimated_baseline_tokens = estimated_baseline_tokens

    def run(self, text: str, *, debug: bool = False, confirmed: bool = False) -> PipelineResult:
        started = time.perf_counter()
        self.bus.emit(events.REQUEST_RECEIVED, {"text": text})
        normalized = normalize(text)
        cache_hit = self._cache_lookup(text, normalized)
        match = MatchSnapshot()
        llm_used = False
        proposal: HermesProposal | None = None
        argv: list[str] = []
        steps: list[FlowStep] = []
        reason = ""
        prompt_tokens = 0
        completion_tokens = 0
        cache_layer = ""
        verdict: SecurityVerdict | None = None

        if cache_hit and (cache_hit.argv or cache_hit.steps):
            steps = normalize_steps(cache_hit.steps or cache_hit.argv)
            argv = flatten_argv(steps) or list(cache_hit.argv)
            cache_layer = cache_hit.layer
            match = MatchSnapshot(
                intent_name=cache_hit.intent_name,
                intent_confidence=1.0,
                entity_name=cache_hit.entity_name,
                entity_confidence=1.0,
                provider_name=cache_hit.provider_name,
                provider_confidence=1.0 if cache_hit.provider_name else 0.0,
                flow_id=cache_hit.flow_id,
                flow_confidence=cache_hit.flow_confidence or 1.0,
                combined=cache_hit.flow_confidence or 1.0,
                known=True,
                method=f"cache_{cache_hit.layer.lower()}",
            )
            self.bus.emit(events.CACHE_HIT, {"layer": cache_layer, "flow_id": match.flow_id})
            self.bus.emit(events.REQUEST_MATCHED, {"flow_id": match.flow_id, "layer": cache_layer})

        if not steps:
            match = self._match(normalized, original=text)
            if match.intent_name and self.cache:
                l3 = self.cache.get_intent_entity(match.intent_name, match.entity_name)
                if l3 and (l3.argv or l3.steps):
                    steps = normalize_steps(l3.steps or l3.argv)
                    argv = flatten_argv(steps) or list(l3.argv)
                    cache_layer = "L3"
                    match.flow_id = l3.flow_id or match.flow_id
                    match.known = True
                    match.method = "cache_l3"
                    self.bus.emit(events.CACHE_HIT, {"layer": "L3", "flow_id": match.flow_id})
            if not steps and match.known and match.flow_id:
                known = self.knowledge.find_flow(match.intent_name or "", match.entity_name)
                if known:
                    flow_id, confidence, known_raw = known
                    match.flow_id = flow_id
                    match.flow_confidence = confidence
                    match.combined = combined_confidence(
                        match.intent_confidence,
                        match.entity_confidence or 1.0,
                        match.provider_confidence,
                        confidence,
                    )
                    known_steps = normalize_steps(known_raw)
                    if meets_threshold(match.combined, self.confidence_threshold) and known_steps:
                        steps = known_steps
                        argv = flatten_argv(steps)
                        if self.cache and not contains_query_token(steps):
                            l4 = self.cache.get_flow(flow_id)
                            if l4 and (l4.argv or l4.steps):
                                steps = normalize_steps(l4.steps or l4.argv)
                                argv = flatten_argv(steps) or list(l4.argv)
                                cache_layer = "L4"
                        self.bus.emit(events.REQUEST_MATCHED, {"flow_id": match.flow_id})

        if not steps:
            if self.llm is None:
                return self._finish(
                    started,
                    status="error",
                    match=match,
                    llm_used=False,
                    message="unknown request and no LLM provider configured",
                    debug=debug,
                    text=text,
                    normalized=normalized,
                    cache_layer=cache_layer,
                )
            try:
                context = {
                    "request": text,
                    "normalized": normalized,
                    "known_intents": [name for _, name, _ in self.knowledge.intent_aliases()],
                    "candidate_entities": [name for _, name, _ in self.knowledge.entity_names()],
                    "available_providers": _provider_names(self.knowledge),
                    "available_actions": _action_names(self.knowledge),
                }
                llm_result = self.llm.generate_structured(redact_mapping(context))
            except Exception as exc:  # noqa: BLE001 — surface provider errors to the API
                return self._finish(
                    started,
                    status="error",
                    match=match,
                    llm_used=True,
                    message=str(exc),
                    debug=debug,
                    text=text,
                    normalized=normalized,
                    cache_layer=cache_layer,
                )
            llm_used = True
            proposal = llm_result.proposal
            prompt_tokens = llm_result.usage.prompt_tokens
            completion_tokens = llm_result.usage.completion_tokens
            self.bus.emit(events.LLM_CALLED, {"reason": "unknown_flow"})
            try:
                steps = compile_proposal(proposal)
                argv = flatten_argv(steps)
            except CompileError as exc:
                return self._finish(
                    started,
                    status="error",
                    match=match,
                    llm_used=True,
                    message=str(exc),
                    debug=debug,
                    text=text,
                    normalized=normalized,
                    proposal=proposal,
                    cache_layer=cache_layer,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
            if proposal.intent:
                match.intent_name = match.intent_name or proposal.intent.name
                match.intent_confidence = match.intent_confidence or proposal.intent.confidence
            if proposal.entities:
                match.entity_name = match.entity_name or proposal.entities[0].name
                match.entity_confidence = match.entity_confidence or proposal.entities[0].confidence
                match.query = match.query or proposal.entities[0].name
            if proposal.provider:
                match.provider_name = proposal.provider.name
            reason = proposal.reason

        if not argv:
            argv = flatten_argv(steps)
        parameters = self._bind_parameters(match, text)
        for step in steps:
            preview = interpolate_command(step.argv, parameters) if step.argv else ["http"]
            level = SecurityLevel(step.security_level) if step.security_level is not None else None
            verdict = evaluate(
                preview or ["http"],
                confirmed=confirmed,
                policy=self.security_policy,
                level=level,
            )
            if verdict.decision is Decision.DENY:
                self.bus.emit(events.EXECUTION_DENIED, {"argv": preview, "reason": verdict.reason})
                return self._finish(
                    started,
                    status="denied",
                    match=match,
                    llm_used=llm_used,
                    argv=argv,
                    message=verdict.reason,
                    debug=debug,
                    text=text,
                    normalized=normalized,
                    proposal=proposal,
                    verdict=verdict,
                    cache_layer=cache_layer,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    steps=steps,
                )
            if verdict.decision is Decision.CONFIRM:
                return self._finish(
                    started,
                    status="confirm_required",
                    match=match,
                    llm_used=llm_used,
                    argv=argv,
                    message=verdict.reason,
                    debug=debug,
                    text=text,
                    normalized=normalized,
                    proposal=proposal,
                    verdict=verdict,
                    cache_layer=cache_layer,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    steps=steps,
                )

        self.bus.emit(events.EXECUTION_STARTED, {"argv": argv, "steps": len(steps)})
        outcome = self._run_steps(steps, parameters)
        status = "success" if outcome.success else "failed"
        self.bus.emit(
            events.EXECUTION_COMPLETED if outcome.success else events.EXECUTION_FAILED,
            {"argv": argv, "success": outcome.success},
        )
        return self._finish(
            started,
            status=status,
            match=match,
            llm_used=llm_used,
            argv=argv,
            message=reason or (outcome.error if not outcome.success else "ok"),
            debug=debug,
            text=text,
            normalized=normalized,
            proposal=proposal,
            verdict=verdict,
            execution=outcome,
            cache_layer=cache_layer,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            steps=steps,
        )

    def _cache_lookup(self, text: str, normalized: str) -> CachedResolution | None:
        if self.cache is None:
            return None
        return lookup_layers(self.cache, phrase=text, normalized=normalized)

    def _match(self, normalized: str, *, original: str = "") -> MatchSnapshot:
        intent_hit = longest_prefix_match(normalized, self.knowledge.intent_aliases())
        entity_hit = None
        remainder = normalized
        if intent_hit:
            remainder = intent_hit.remainder
            providers = _provider_alias_list(self.knowledge)
            provider_hit = match_entity(remainder, providers) if providers else None
            # Strip a trailing/leading provider mention so entity matching stays clean.
            entity_token = remainder
            provider_name = None
            provider_conf = 0.0
            if provider_hit and provider_hit.method in {"exact", "prefix"}:
                provider_name = provider_hit.name
                provider_conf = provider_hit.confidence
                entity_token = (
                    remainder[: remainder.find(provider_hit.key)].strip()
                    if provider_hit.key in remainder
                    else remainder
                )
            entity_hit = match_entity(
                entity_token,
                self.knowledge.entity_names(),
                embedder=self.embedder,
                semantic_threshold=self.semantic_threshold,
            )
        else:
            provider_name = None
            provider_conf = 0.0

        flow = None
        if intent_hit:
            flow = self.knowledge.find_flow(
                intent_hit.name, entity_hit.name if entity_hit else None
            )
        combined = combined_confidence(
            intent_hit.confidence if intent_hit else 0.0,
            entity_hit.confidence if entity_hit else 0.0,
            provider_conf,
            flow[1] if flow else 0.0,
        )
        known = bool(flow and meets_threshold(combined, self.confidence_threshold) and flow[2])
        ambiguous = bool(entity_hit and entity_hit.method in {"prefix", "fuzzy", "semantic"})
        query = ""
        if entity_hit:
            query = entity_hit.name
        elif intent_hit and intent_hit.remainder:
            query = original_span(original, intent_hit.remainder) or intent_hit.remainder
        return MatchSnapshot(
            intent_name=intent_hit.name if intent_hit else None,
            intent_confidence=intent_hit.confidence if intent_hit else 0.0,
            entity_name=entity_hit.name if entity_hit else None,
            entity_confidence=entity_hit.confidence if entity_hit else 0.0,
            provider_name=provider_name,
            provider_confidence=provider_conf,
            flow_id=flow[0] if flow else None,
            flow_confidence=flow[1] if flow else 0.0,
            combined=combined,
            known=known,
            method=(entity_hit.method if entity_hit else (intent_hit.method if intent_hit else "")),
            ambiguous_entity=ambiguous,
            query=query,
        )

    def _bind_parameters(self, match: MatchSnapshot, text: str) -> dict[str, Any]:
        params: dict[str, Any] = {
            "query": match.entity_name or match.query or "",
            "entity": match.entity_name or match.query or "",
            "intent": match.intent_name or "",
            "text": text,
        }
        getter = getattr(self.knowledge, "entity_metadata", None)
        if getter and match.entity_name:
            meta = getter(match.entity_name) or {}
            if isinstance(meta, dict):
                for key, value in meta.items():
                    if isinstance(value, (str, int, float)):
                        params[str(key)] = value
        return params

    def _run_steps(self, steps: list[FlowStep], parameters: dict[str, Any]) -> ExecuteResult:
        context = dict(parameters)
        last = ExecuteResult(success=True, stdout="ok")
        for step in steps:
            argv = interpolate_command(step.argv, context) if step.argv else []
            extra = interpolate_mapping(step.extra, context)
            extra_map = extra if isinstance(extra, dict) else {}
            if not argv:
                is_http = (step.executor or "").lower() == "http" or extra_map.get("url")
                argv = ["http"] if is_http else []
            if not argv:
                return ExecuteResult(success=False, error="empty command")
            executor = executor_for(step.executor, fallback=self.executor)
            last = executor.execute(
                ExecuteRequest(argv=argv, extra=extra_map, timeout_s=self.timeout_s)
            )
            if not last.success:
                return last
            context.update(json_bindings(last.stdout))
        return last

    def _finish(
        self,
        started: float,
        *,
        status: str,
        match: MatchSnapshot,
        llm_used: bool,
        message: str = "",
        argv: list[str] | None = None,
        debug: bool = False,
        text: str = "",
        normalized: str = "",
        proposal: HermesProposal | None = None,
        verdict: SecurityVerdict | None = None,
        execution: ExecuteResult | None = None,
        cache_layer: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        steps: list[FlowStep] | None = None,
    ) -> PipelineResult:
        elapsed = int((time.perf_counter() - started) * 1000)
        actual_tokens = prompt_tokens + completion_tokens
        estimated_without, saved = estimated_tokens_saved(
            llm_used=llm_used,
            actual_tokens=actual_tokens,
            baseline=self.estimated_baseline_tokens,
        )
        debug_payload: dict[str, Any] = {}
        if debug:
            debug_payload = {
                "input": text,
                "normalization": {"text": normalized},
                "intent": {"value": match.intent_name, "confidence": match.intent_confidence},
                "entity": {"value": match.entity_name, "confidence": match.entity_confidence},
                "provider": {
                    "value": match.provider_name,
                    "confidence": match.provider_confidence,
                },
                "flow": {"id": match.flow_id, "confidence": match.flow_confidence},
                "combined_confidence": match.combined,
                "cache_layer": cache_layer or None,
                "match_method": match.method,
                "llm_used": llm_used,
                "argv": argv or [],
                "estimated_tokens_without_econ": estimated_without,
                "tokens_saved": saved,
                "security": {
                    "decision": verdict.decision if verdict else None,
                    "reason": verdict.reason if verdict else None,
                    "level": int(verdict.level) if verdict else None,
                },
                "execution": None
                if execution is None
                else {
                    "success": execution.success,
                    "exit_code": execution.exit_code,
                    "stdout": execution.stdout,
                    "stderr": execution.stderr,
                    "error": execution.error,
                },
            }
        return PipelineResult(
            status=status,
            intent=match.intent_name,
            entity=match.entity_name,
            flow_id=match.flow_id,
            execution_time_ms=elapsed,
            llm_used=llm_used,
            argv=argv or [],
            message=message,
            security_decision=str(verdict.decision) if verdict else "",
            execution=execution,
            debug=debug_payload,
            proposal=proposal,
            cache_layer=cache_layer,
            combined_confidence=match.combined,
            match_method=match.method,
            provider=match.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_tokens_without_econ=estimated_without,
            tokens_saved=saved,
            original_text=text,
            normalized_text=normalized,
            ambiguous_entity=match.ambiguous_entity,
            steps=[step.to_dict() for step in steps or []],
        )


def _provider_names(knowledge: KnowledgeSource) -> list[str]:
    getter = getattr(knowledge, "provider_names", None)
    if getter is None:
        return []
    return [name for _, name, _ in getter()]


def _provider_alias_list(knowledge: KnowledgeSource) -> list[tuple[str, str, float]]:
    getter = getattr(knowledge, "provider_names", None)
    if getter is None:
        return []
    return list(getter())


def _action_names(knowledge: KnowledgeSource) -> list[str]:
    getter = getattr(knowledge, "action_names", None)
    if getter is None:
        return []
    return list(getter())


__all__ = ["KnowledgeSource", "MatchSnapshot", "Pipeline", "PipelineResult"]
