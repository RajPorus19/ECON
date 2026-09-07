"""Runtime pipeline: normalize → match → (Hermes) → validate → execute."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from core import events
from core.compiler import CompileError, first_argv
from core.events import EventBus
from core.execution import ExecuteRequest, ExecuteResult, Executor
from core.llm import HermesProposal, LLMProvider
from core.matching import exact_or_alias_match, longest_prefix_match
from core.normalize import normalize
from core.security import Decision, SecurityVerdict, evaluate


@dataclass
class MatchSnapshot:
    intent_name: str | None = None
    intent_confidence: float = 0.0
    entity_name: str | None = None
    entity_confidence: float = 0.0
    flow_id: str | None = None
    flow_confidence: float = 0.0
    known: bool = False


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


class KnowledgeSource(Protocol):
    def intent_aliases(self) -> list[tuple[str, str, float]]: ...

    def entity_names(self) -> list[tuple[str, str, float]]: ...

    def find_flow(
        self, intent_name: str, entity_name: str | None
    ) -> tuple[str, float, list[str]] | None:
        """Return (flow_id, confidence, argv) if a known flow exists."""
        ...


class Pipeline:
    def __init__(
        self,
        *,
        knowledge: KnowledgeSource,
        executor: Executor,
        llm: LLMProvider | None,
        bus: EventBus | None = None,
        confidence_threshold: float = 0.90,
        timeout_s: float = 30.0,
    ) -> None:
        self.knowledge = knowledge
        self.executor = executor
        self.llm = llm
        self.bus = bus or EventBus()
        self.confidence_threshold = confidence_threshold
        self.timeout_s = timeout_s

    def run(self, text: str, *, debug: bool = False, confirmed: bool = False) -> PipelineResult:
        started = time.perf_counter()
        self.bus.emit(events.REQUEST_RECEIVED, {"text": text})
        normalized = normalize(text)
        match = self._match(normalized)
        llm_used = False
        proposal: HermesProposal | None = None
        argv: list[str] = []
        reason = ""

        if match.known and match.flow_id:
            known = self.knowledge.find_flow(match.intent_name or "", match.entity_name)
            if known:
                _flow_id, confidence, known_argv = known
                if confidence >= self.confidence_threshold and known_argv:
                    argv = known_argv
                    self.bus.emit(events.REQUEST_MATCHED, {"flow_id": match.flow_id})

        if not argv:
            if self.llm is None:
                return self._finish(
                    started,
                    status="error",
                    match=match,
                    llm_used=False,
                    message="unknown request and no LLM provider configured",
                    debug=debug,
                    normalized=normalized,
                )
            try:
                llm_result = self.llm.generate_structured(
                    {
                        "request": text,
                        "normalized": normalized,
                        "known_intents": [name for _, name, _ in self.knowledge.intent_aliases()],
                        "candidate_entities": [
                            name for _, name, _ in self.knowledge.entity_names()
                        ],
                    }
                )
            except Exception as exc:  # noqa: BLE001 — surface provider errors to the API
                return self._finish(
                    started,
                    status="error",
                    match=match,
                    llm_used=True,
                    message=str(exc),
                    debug=debug,
                    normalized=normalized,
                )
            llm_used = True
            proposal = llm_result.proposal
            self.bus.emit(events.LLM_CALLED, {"reason": "unknown_flow"})
            try:
                argv = first_argv(proposal)
            except CompileError as exc:
                return self._finish(
                    started,
                    status="error",
                    match=match,
                    llm_used=True,
                    message=str(exc),
                    debug=debug,
                    normalized=normalized,
                    proposal=proposal,
                )
            if proposal.intent:
                match.intent_name = match.intent_name or proposal.intent.name
            if proposal.entities:
                match.entity_name = match.entity_name or proposal.entities[0].name
            reason = proposal.reason

        verdict = evaluate(argv, confirmed=confirmed)
        if verdict.decision is Decision.DENY:
            self.bus.emit(events.EXECUTION_DENIED, {"argv": argv, "reason": verdict.reason})
            return self._finish(
                started,
                status="denied",
                match=match,
                llm_used=llm_used,
                argv=argv,
                message=verdict.reason,
                debug=debug,
                normalized=normalized,
                proposal=proposal,
                verdict=verdict,
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
                normalized=normalized,
                proposal=proposal,
                verdict=verdict,
            )

        self.bus.emit(events.EXECUTION_STARTED, {"argv": argv})
        outcome = self.executor.execute(ExecuteRequest(argv=argv, timeout_s=self.timeout_s))
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
            normalized=normalized,
            proposal=proposal,
            verdict=verdict,
            execution=outcome,
        )

    def _match(self, normalized: str) -> MatchSnapshot:
        intent_hit = longest_prefix_match(normalized, self.knowledge.intent_aliases())
        entity_hit = None
        remainder = normalized
        if intent_hit:
            remainder = intent_hit.remainder
            entity_hit = exact_or_alias_match(remainder, self.knowledge.entity_names())
            if entity_hit is None and remainder:
                entity_hit = longest_prefix_match(remainder, self.knowledge.entity_names())
        flow = None
        if intent_hit:
            flow = self.knowledge.find_flow(
                intent_hit.name, entity_hit.name if entity_hit else None
            )
        known = bool(flow and flow[1] >= self.confidence_threshold and flow[2])
        return MatchSnapshot(
            intent_name=intent_hit.name if intent_hit else None,
            intent_confidence=intent_hit.confidence if intent_hit else 0.0,
            entity_name=entity_hit.name if entity_hit else None,
            entity_confidence=entity_hit.confidence if entity_hit else 0.0,
            flow_id=flow[0] if flow else None,
            flow_confidence=flow[1] if flow else 0.0,
            known=known,
        )

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
        normalized: str = "",
        proposal: HermesProposal | None = None,
        verdict: SecurityVerdict | None = None,
        execution: ExecuteResult | None = None,
    ) -> PipelineResult:
        elapsed = int((time.perf_counter() - started) * 1000)
        debug_payload: dict[str, Any] = {}
        if debug:
            debug_payload = {
                "normalization": {"text": normalized},
                "intent": {"value": match.intent_name, "confidence": match.intent_confidence},
                "entity": {"value": match.entity_name, "confidence": match.entity_confidence},
                "flow": {"id": match.flow_id, "confidence": match.flow_confidence},
                "llm_used": llm_used,
                "argv": argv or [],
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
        )


# Re-export for callers that compile multiple actions.
__all__ = ["KnowledgeSource", "MatchSnapshot", "Pipeline", "PipelineResult"]
