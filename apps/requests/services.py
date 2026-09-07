"""Django-backed knowledge + pipeline factory."""

from __future__ import annotations

from django.conf import settings

from apps.execution.models import ExecutionAudit, ExecutionStatus
from apps.flows.models import ActionVersion, Flow
from apps.knowledge.models import Alias, Entity, Intent, IntentAlias
from apps.llm.models import LlmCall
from apps.requests.models import RequestLog
from core.engine import Pipeline, PipelineResult
from core.events import EventBus
from core.execution.host_agent import HostAgentExecutor
from core.execution.local import LocalSubprocessExecutor
from core.llm.ollama import OllamaProvider


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

    def find_flow(
        self, intent_name: str, entity_name: str | None
    ) -> tuple[str, float, list[str]] | None:
        if not intent_name:
            return None
        qs = Flow.objects.filter(intent__name=intent_name, enabled=True)
        if entity_name:
            qs = qs.filter(nodes__entity__name=entity_name).distinct()
        flow = qs.order_by("-confidence", "-usage_count").first()
        if flow is None and entity_name:
            flow = (
                Flow.objects.filter(intent__name=intent_name, enabled=True)
                .order_by("-confidence", "-usage_count")
                .first()
            )
        if flow is None:
            return None
        argv = _argv_for_flow(flow)
        if not argv:
            return None
        return str(flow.pk), float(flow.confidence), argv


def _argv_for_flow(flow: Flow) -> list[str]:
    node = flow.nodes.filter(action__isnull=False).order_by("position").first()
    if node is None or node.action_id is None:
        return []
    version = (
        ActionVersion.objects.filter(action_id=node.action_id, enabled=True)
        .order_by("-version")
        .first()
    )
    if version is None:
        return []
    definition = version.definition or {}
    if isinstance(definition.get("argv"), list) and definition["argv"]:
        return [str(part) for part in definition["argv"]]
    if isinstance(node.config.get("argv"), list) and node.config["argv"]:
        return [str(part) for part in node.config["argv"]]
    return []


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
        bus=EventBus(),
        confidence_threshold=float(str(cfg.get("CONFIDENCE_THRESHOLD", 0.90))),
        timeout_s=float(str(cfg.get("EXECUTION_TIMEOUT", 30))),
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
        if result.flow_id and result.flow_id.isdigit():
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
            prompt={"text": text},
            response=result.proposal.model_dump() if result.proposal else {},
            success=result.status in {"success", "confirm_required", "denied"},
            error=result.message if result.status == "error" else "",
            duration_ms=result.execution_time_ms,
        )
    return log


def run_execute(
    text: str,
    *,
    debug: bool = False,
    confirmed: bool = False,
    pipeline: Pipeline | None = None,
) -> PipelineResult:
    from core.normalize import normalize

    engine = pipeline or build_pipeline()
    result = engine.run(text, debug=debug, confirmed=confirmed)
    persist_result(text, normalize(text), result)
    return result
