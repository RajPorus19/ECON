"""Django-backed knowledge + pipeline factory."""

from __future__ import annotations

from typing import Any

from django.conf import settings

from apps.execution.models import ExecutionAudit, ExecutionStatus
from apps.flows.models import Action, ActionVersion, Flow, FlowNode
from apps.knowledge.models import Alias, Entity, Intent, IntentAlias, Provider
from apps.llm.models import LlmCall
from apps.requests.models import RequestLog
from apps.requests.runtime import bus_with_redis, get_phrase_cache
from core.cache import CachedResolution
from core.embeddings import HashEmbeddingBackend
from core.engine import Pipeline, PipelineResult
from core.execution import FlowStep
from core.execution.host_agent import HostAgentExecutor
from core.execution.local import LocalSubprocessExecutor
from core.llm.ollama import OllamaProvider
from core.normalize import normalize
from core.secrets import redact_mapping
from core.security import policy_from_mapping


class DjangoKnowledge:
    def intent_aliases(self) -> list[tuple[str, str, float]]:
        rows = IntentAlias.objects.select_related("intent").values_list(
            "normalized_phrase", "intent__name", "confidence"
        )
        return [(phrase, name, float(conf)) for phrase, name, conf in rows]

    def entity_names(self) -> list[tuple[str, str, float]]:
        names: list[tuple[str, str, float]] = []
        for normalized, name, conf in Entity.objects.values_list(
            "normalized_name", "name", "confidence"
        ):
            names.append((normalized, name, float(conf)))
        for normalized, name, conf in Alias.objects.select_related("entity").values_list(
            "normalized_alias", "entity__name", "confidence"
        ):
            names.append((normalized, name, float(conf)))
        return names

    def provider_names(self) -> list[tuple[str, str, float]]:
        rows = Provider.objects.values_list("name", "name")
        return [(str(name).lower(), str(name), 1.0) for name, _ in rows]

    def action_names(self) -> list[str]:
        return list(Action.objects.values_list("name", flat=True))

    def entity_metadata(self, entity_name: str) -> dict[str, Any]:
        entity = Entity.objects.filter(name=entity_name).first()
        if entity is None:
            entity = Entity.objects.filter(normalized_name=entity_name.lower()).first()
        if entity is None or not isinstance(entity.metadata, dict):
            return {}
        return dict(entity.metadata)

    def find_flow(
        self, intent_name: str, entity_name: str | None
    ) -> tuple[str, float, list[str] | list[dict[str, Any]]] | None:
        if not intent_name:
            return None
        qs = Flow.objects.filter(intent__name=intent_name, enabled=True)
        if entity_name:
            qs = qs.filter(nodes__entity__name=entity_name).distinct()
        flow = qs.order_by("-version", "-confidence", "-usage_count").first()
        if flow is None and entity_name:
            flow = (
                Flow.objects.filter(intent__name=intent_name, enabled=True)
                .order_by("-version", "-confidence", "-usage_count")
                .first()
            )
        if flow is None:
            return None
        steps = _steps_for_flow(flow, entity_name)
        if not steps:
            return None
        return str(flow.pk), float(flow.confidence), [step.to_dict() for step in steps]


def _steps_for_flow(flow: Flow, entity_name: str | None) -> list[FlowStep]:
    entity = None
    if entity_name:
        entity = Entity.objects.filter(name=entity_name).first()
    metadata = dict(entity.metadata) if entity and isinstance(entity.metadata, dict) else {}
    query = (entity.name if entity else entity_name) or ""
    action_nodes = list(flow.nodes.filter(action__isnull=False).order_by("position"))
    action_names = [node.action.name for node in action_nodes if node.action]
    intent = flow.intent
    intent_name = intent.name if intent is not None else ""

    if intent_name == "play_media" and any(name.startswith("jellyfin.") for name in action_names):
        from plugins.jellyfin import compose_play_steps

        return compose_play_steps(query=query, metadata=metadata)
    if "jellyfin.play" in action_names and "jellyfin.search" not in action_names:
        from plugins.jellyfin import compose_play_steps

        return compose_play_steps(query=query, metadata=metadata)

    steps: list[FlowStep] = []
    for node in action_nodes:
        step = _step_for_node(node, metadata=metadata, query=query)
        if step is not None:
            steps.append(step)
    return steps


def _step_for_node(node: FlowNode, *, metadata: dict[str, Any], query: str) -> FlowStep | None:
    action = node.action
    if action is None:
        return None
    name = action.name
    if name == "steam.launch":
        from plugins.steam import resolve_launch

        return resolve_launch(metadata=metadata, entity_name=query)
    if name.startswith("jellyfin."):
        from plugins.jellyfin import resolve_action

        return resolve_action(name, query=query, metadata=metadata)
    argv: list[str] = []
    extra = dict(node.config.get("extra") or {}) if isinstance(node.config, dict) else {}
    if isinstance(node.config.get("argv"), list) and node.config["argv"]:
        argv = [str(part) for part in node.config["argv"]]
    else:
        version = (
            ActionVersion.objects.filter(action_id=action.pk, enabled=True)
            .order_by("-version")
            .first()
        )
        definition = (version.definition or {}) if version else {}
        if isinstance(definition.get("argv"), list) and definition["argv"]:
            argv = [str(part) for part in definition["argv"]]
        elif isinstance(definition.get("command"), list) and definition["command"]:
            argv = [str(part) for part in definition["command"]]
        if isinstance(definition.get("extra"), dict):
            extra = dict(definition["extra"])
    executor = action.executor or "shell"
    if not argv and executor == "http":
        argv = ["http"]
    if not argv:
        return None
    return FlowStep(
        executor=executor,
        argv=argv,
        extra=extra,
        security_level=action.security_level,
    )


def build_executor():
    cfg = settings.ECON
    mode = str(cfg.get("EXECUTION_MODE", "local"))
    if mode == "host_agent":
        return HostAgentExecutor(
            base_url=str(cfg["HOST_AGENT_URL"]),
            token=str(cfg["HOST_AGENT_TOKEN"]),
            timeout_s=float(str(cfg.get("EXECUTION_TIMEOUT", 30))) + 5,
        )
    return LocalSubprocessExecutor()


def build_llm() -> OllamaProvider:
    cfg = settings.ECON
    return OllamaProvider(base_url=str(cfg["LLM_BASE_URL"]), model=str(cfg["LLM_MODEL"]))


def build_pipeline(llm: OllamaProvider | None | object = ...) -> Pipeline:
    cfg = settings.ECON
    provider = build_llm() if llm is ... else llm  # type: ignore[assignment]
    return Pipeline(
        knowledge=DjangoKnowledge(),
        executor=build_executor(),
        llm=provider,  # type: ignore[arg-type]
        bus=bus_with_redis(),
        cache=get_phrase_cache(),
        embedder=HashEmbeddingBackend(),
        confidence_threshold=float(str(cfg.get("CONFIDENCE_THRESHOLD", 0.90))),
        semantic_threshold=float(str(cfg.get("SEMANTIC_THRESHOLD", 0.82))),
        timeout_s=float(str(cfg.get("EXECUTION_TIMEOUT", 30))),
        security_policy=policy_from_mapping(
            {
                "destructive_actions": str(cfg.get("DESTRUCTIVE_ACTIONS", "deny")),
                "filesystem_actions": str(cfg.get("FILESYSTEM_ACTIONS", "confirm")),
            }
        ),
        estimated_baseline_tokens=int(str(cfg.get("ESTIMATED_BASELINE_TOKENS", 1200))),
    )


def persist_result(text: str, normalized: str, result: PipelineResult) -> RequestLog:
    audit = None
    if result.argv:
        status_map = {
            "success": ExecutionStatus.SUCCESS,
            "failed": ExecutionStatus.FAILED,
            "denied": ExecutionStatus.DENIED,
            "confirm_required": ExecutionStatus.CONFIRM_REQUIRED,
        }
        audit = ExecutionAudit.objects.create(
            request_text=text,
            argv=result.argv,
            security_decision=result.security_decision,
            status=status_map.get(result.status, ExecutionStatus.FAILED),
            result={
                "stdout": result.execution.stdout if result.execution else "",
                "stderr": result.execution.stderr if result.execution else "",
                "error": result.execution.error if result.execution else result.message,
                "exit_code": result.execution.exit_code if result.execution else None,
            },
            duration_ms=result.execution_time_ms,
        )
        if result.intent:
            intent = Intent.objects.filter(name=result.intent).first()
            if intent:
                audit.intent = intent
        if result.entity:
            entity = Entity.objects.filter(name=result.entity).first()
            if entity:
                audit.entity = entity
        if result.flow_id and str(result.flow_id).isdigit():
            audit.flow_id = int(result.flow_id)
        audit.save()

    log = RequestLog.objects.create(
        text=text,
        normalized_text=normalized,
        llm_used=result.llm_used,
        status=result.status,
        execution=audit,
        duration_ms=result.execution_time_ms,
        debug=result.debug,
        proposal=result.proposal.model_dump() if result.proposal else {},
        cache_layer=result.cache_layer,
        match_method=result.match_method,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        estimated_tokens_without_econ=result.estimated_tokens_without_econ,
        tokens_saved=result.tokens_saved,
    )
    if result.intent:
        log.intent = Intent.objects.filter(name=result.intent).first()
    if result.entity:
        log.entity = Entity.objects.filter(name=result.entity).first()
    if result.flow_id and str(result.flow_id).isdigit():
        log.flow_id = int(result.flow_id)
    log.save()

    if result.llm_used:
        LlmCall.objects.create(
            request=log,
            reason="unknown_flow" if not result.flow_id else "low_confidence",
            model=str(settings.ECON.get("LLM_MODEL", "")),
            prompt=redact_mapping({"text": text}),
            response=result.proposal.model_dump() if result.proposal else {},
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            success=result.status in {"success", "confirm_required", "denied"},
            error=result.message if result.status == "error" else "",
            duration_ms=result.execution_time_ms,
        )

    if result.status in {"success", "failed"} and (result.argv or result.steps):
        cache = get_phrase_cache()
        cached = CachedResolution(
            intent_name=result.intent,
            entity_name=result.entity,
            provider_name=result.provider,
            flow_id=result.flow_id,
            flow_confidence=result.combined_confidence or 1.0,
            argv=result.argv,
            steps=result.steps,
        )
        if result.status == "success":
            cache.put_exact(text, cached)
            cache.put_normalized(normalized, cached)
            if result.intent:
                cache.put_intent_entity(result.intent, result.entity, cached)
            if result.flow_id:
                cache.put_flow(result.flow_id, cached)

    from apps.knowledge.tasks import enqueue_learn_from_execution

    enqueue_learn_from_execution(log.pk)
    return log


def run_execute(
    text: str,
    *,
    debug: bool = False,
    confirmed: bool = False,
    pipeline: Pipeline | None = None,
) -> PipelineResult:
    engine = pipeline or build_pipeline()
    result = engine.run(text, debug=debug, confirmed=confirmed)
    persist_result(text, normalize(text), result)
    return result
