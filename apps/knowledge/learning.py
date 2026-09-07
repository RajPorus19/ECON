"""Persist Hermes proposals into versioned knowledge. Never mutate an existing flow body."""

from __future__ import annotations

import json

from django.utils import timezone

from apps.flows.models import Action, ActionVersion, Flow, FlowEdge, FlowNode
from apps.knowledge.models import Alias, AliasCandidate, Entity, Intent, IntentAlias, Provider
from core.compiler import CompileError, argv_from_action, compile_proposal
from core.confidence import apply_outcome
from core.execution import FlowStep, normalize_steps
from core.learning import (
    next_confirmation_count,
    replacement_phrases,
    should_promote_alias,
    steps_signature,
    strip_trailing_query,
    template_steps,
    trigger_phrases,
)
from core.llm import HermesProposal
from core.normalize import normalize


def next_flow_version(name: str) -> int:
    last = (
        Flow.objects.filter(name=name)
        .order_by("-version")
        .values_list("version", flat=True)
        .first()
    )
    return 1 if last is None else int(last) + 1


def next_action_version(action: Action) -> int:
    last = action.versions.order_by("-version").values_list("version", flat=True).first()
    return 1 if last is None else int(last) + 1


def clone_flow_version(flow: Flow, *, enabled: bool = True) -> Flow:
    """Copy nodes/edges onto a new version. Leaves the source row untouched."""
    clone = Flow.objects.create(
        name=flow.name,
        description=flow.description,
        intent=flow.intent,
        version=next_flow_version(flow.name),
        confidence=flow.confidence,
        enabled=enabled,
    )
    key_map: dict[int, FlowNode] = {}
    for node in flow.nodes.all().order_by("position"):
        key_map[node.pk] = FlowNode.objects.create(
            flow=clone,
            node_key=node.node_key,
            node_type=node.node_type,
            action=node.action,
            entity=node.entity,
            provider=node.provider,
            position=node.position,
            config=node.config,
        )
    for edge in flow.edges.all():
        FlowEdge.objects.create(
            flow=clone,
            source_node=key_map[edge.source_node_id],
            target_node=key_map[edge.target_node_id],
            condition=edge.condition,
        )
    return clone


def apply_graph_version(flow: Flow, payload: dict) -> Flow:
    """Persist node/edge edits onto a new version. Never mutates the source graph."""
    clone = clone_flow_version(flow, enabled=True)
    if "name" in payload and payload["name"]:
        clone.name = str(payload["name"])
    if "description" in payload:
        clone.description = str(payload["description"] or "")
    if "enabled" in payload:
        clone.enabled = bool(payload["enabled"])
    clone.save()

    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    if raw_nodes is None and raw_edges is None:
        flow.enabled = False
        flow.save(update_fields=["enabled"])
        return clone

    old_by_id = {node.pk: node for node in flow.nodes.all()}
    old_by_key = {node.node_key: node for node in flow.nodes.all()}
    clone.edges.all().delete()
    clone.nodes.all().delete()

    key_map: dict[str, FlowNode] = {}
    for index, item in enumerate(raw_nodes or []):
        if not isinstance(item, dict):
            continue
        node_key = str(item.get("node_key") or item.get("id") or f"node_{index}")
        source = None
        raw_id = item.get("id")
        if raw_id is not None and str(raw_id).isdigit():
            source = old_by_id.get(int(raw_id))
        source = source or old_by_key.get(node_key)
        config = dict(item.get("config") or (source.config if source else {}) or {})
        if "x" in item or "y" in item:
            config["ui"] = {"x": item.get("x"), "y": item.get("y")}
        raw_pos = item.get("position")
        position = int(raw_pos) if isinstance(raw_pos, (int, float, str)) else index
        created = FlowNode.objects.create(
            flow=clone,
            node_key=node_key[:64],
            node_type=str(item.get("node_type") or (source.node_type if source else "action")),
            action=source.action if source else None,
            entity=source.entity if source else None,
            provider=source.provider if source else None,
            position=position,
            config=config,
        )
        key_map[str(item.get("id") or node_key)] = created
        key_map[node_key] = created
        if source:
            key_map[str(source.pk)] = created

    for item in raw_edges or []:
        if not isinstance(item, dict):
            continue
        source_ref = str(item.get("source") or item.get("source_node") or "")
        target_ref = str(item.get("target") or item.get("target_node") or "")
        source_node = key_map.get(source_ref)
        target_node = key_map.get(target_ref)
        if source_node is None or target_node is None:
            continue
        FlowEdge.objects.create(
            flow=clone,
            source_node=source_node,
            target_node=target_node,
            condition=item.get("condition") or {},
        )

    flow.enabled = False
    flow.save(update_fields=["enabled"])
    return clone


def apply_usage(
    *, intent: Intent | None, entity: Entity | None, flow: Flow | None, success: bool
) -> None:
    now = timezone.now()
    for obj in (intent, entity, flow):
        if obj is None:
            continue
        obj.confidence = apply_outcome(float(obj.confidence), success=success)
        obj.usage_count = int(obj.usage_count) + 1
        if hasattr(obj, "last_used_at"):
            obj.last_used_at = now
        if hasattr(obj, "success_count") and success:
            obj.success_count = int(obj.success_count) + 1
        if hasattr(obj, "failure_count") and not success:
            obj.failure_count = int(obj.failure_count) + 1
        obj.save()


def record_alias_candidate(
    *,
    remainder: str,
    entity: Entity,
    success: bool,
    required_confirmations: int,
) -> Alias | None:
    phrase = remainder.strip()
    if not phrase or phrase == entity.normalized_name:
        return None
    candidate, _ = AliasCandidate.objects.get_or_create(
        normalized_phrase=phrase,
        entity=entity,
        defaults={"confirmations": 0},
    )
    candidate.confirmations = next_confirmation_count(
        int(candidate.confirmations),
        matched_ambiguously=True,
        success=success,
    )
    candidate.last_seen_at = timezone.now()
    candidate.save(update_fields=["confirmations", "last_seen_at"])
    if not success or not should_promote_alias(
        int(candidate.confirmations), required=required_confirmations
    ):
        return None
    alias, _ = Alias.objects.get_or_create(
        entity=entity,
        normalized_alias=phrase,
        defaults={"alias": phrase, "confidence": 0.8, "usage_count": candidate.confirmations},
    )
    return alias


def persist_proposal(
    proposal: HermesProposal,
    argv: list[str],
    *,
    text: str = "",
    normalized: str = "",
    steps: list[FlowStep] | list[dict] | None = None,
    confidence_threshold: float = 0.90,
) -> Flow | None:
    intent = None
    if proposal.intent:
        intent, _ = Intent.objects.get_or_create(
            name=proposal.intent.name,
            defaults={"confidence": proposal.intent.confidence or 0.7},
        )
    else:
        intent, _ = Intent.objects.get_or_create(
            name="shell_execute",
            defaults={"confidence": 0.7},
        )

    entity = None
    for item in proposal.entities:
        entity, created = Entity.objects.get_or_create(
            normalized_name=normalize(item.name),
            defaults={
                "name": item.name,
                "type": item.type or "application",
                "metadata": item.metadata,
                "confidence": item.confidence or 0.6,
            },
        )
        if created is False and item.create:
            # Do not silently rewrite metadata of a learned entity.
            pass

    provider = None
    if proposal.provider:
        provider, _ = Provider.objects.get_or_create(
            name=proposal.provider.name,
            defaults={"type": "plugin", "capabilities": []},
        )

    try:
        compiled = normalize_steps(steps) if steps else compile_proposal(proposal)
    except CompileError:
        compiled = [FlowStep(executor="shell", argv=list(argv))] if argv else []
    if not compiled and argv:
        compiled = [FlowStep(executor="shell", argv=list(argv))]
    if not compiled:
        return None

    ntext = normalized or normalize(text)
    replacements = replacement_phrases(proposal, ntext)
    templated = template_steps(compiled, replacements)
    query_for_triggers = ""
    for phrase in sorted(replacements, key=len, reverse=True):
        if strip_trailing_query(ntext, phrase) != ntext or ntext == normalize(phrase):
            query_for_triggers = phrase
            break
    triggers = trigger_phrases(
        normalized=ntext,
        query=query_for_triggers,
        extra=proposal.triggers,
    )
    bind_intent_triggers(intent, triggers)

    learned_confidence = max(float(confidence_threshold), 0.90)
    existing = _reusable_flow(intent, templated)
    if existing is not None:
        if existing.confidence < learned_confidence:
            existing.confidence = learned_confidence
            existing.save(update_fields=["confidence"])
        return existing

    flow_name = proposal.flow.name if proposal.flow and proposal.flow.name else None
    if not flow_name:
        bits = [intent.name if intent else "request"]
        if entity and not any("{query}" in part for step in templated for part in step.argv):
            extra_blob = json.dumps([step.extra for step in templated])
            if "{query}" not in extra_blob:
                bits.append(entity.name)
        flow_name = " / ".join(bits)

    previous = Flow.objects.filter(name=flow_name, enabled=True).order_by("-version").first()
    flow = Flow.objects.create(
        name=flow_name,
        intent=intent,
        version=next_flow_version(flow_name),
        confidence=learned_confidence,
        enabled=True,
    )
    if previous is not None:
        previous.enabled = False
        previous.save(update_fields=["enabled"])

    parameterized = any("{query}" in part for step in templated for part in step.argv) or any(
        "{query}" in json.dumps(step.extra or {}) for step in templated
    )
    attach_entity = entity if entity and not parameterized else None

    if attach_entity or provider:
        FlowNode.objects.create(
            flow=flow,
            node_key="resolve_entity",
            node_type="resolve_entity",
            entity=attach_entity,
            provider=provider,
            position=0,
        )
    position = 1 if flow.nodes.exists() else 0
    previous_node = flow.nodes.order_by("position").last()
    for index, step in enumerate(templated):
        action = _action_for_step(step)
        node = FlowNode.objects.create(
            flow=flow,
            node_key="execute" if index == 0 else f"execute_{index}",
            node_type="action",
            action=action,
            entity=attach_entity,
            provider=provider,
            position=position + index,
            config={"argv": list(step.argv), "extra": dict(step.extra or {})},
        )
        if previous_node is not None:
            FlowEdge.objects.create(flow=flow, source_node=previous_node, target_node=node)
        previous_node = node
    return flow


def bind_intent_triggers(intent: Intent, phrases: list[str], *, confidence: float = 1.0) -> None:
    for raw in phrases:
        phrase = raw.strip()
        if not phrase:
            continue
        folded = normalize(phrase)
        if not folded:
            continue
        IntentAlias.objects.get_or_create(
            normalized_phrase=folded,
            defaults={"intent": intent, "phrase": phrase, "confidence": confidence},
        )


def _action_for_step(step: FlowStep) -> Action:
    if (step.executor or "").lower() == "http":
        name = "http.request"
        defaults = {
            "type": "http",
            "description": "HTTP request",
            "executor": "http",
            "security_level": 2,
        }
    else:
        name = "shell.execute"
        defaults = {
            "type": "shell",
            "description": "Execute an argv list on the host",
            "executor": "shell",
            "security_level": 1,
        }
    action, created = Action.objects.get_or_create(name=name, defaults=defaults)
    if created or not action.versions.exists():
        ActionVersion.objects.get_or_create(
            action=action,
            version=1,
            defaults={
                "definition": {
                    "executor": action.executor,
                    "argv": list(step.argv),
                    "extra": dict(step.extra or {}),
                },
                "enabled": True,
                "verified": False,
            },
        )
    return action


def _reusable_flow(intent: Intent | None, templated: list[FlowStep]) -> Flow | None:
    if intent is None:
        return None
    wanted = steps_signature(templated)
    for flow in Flow.objects.filter(intent=intent, enabled=True).order_by("-version"):
        if _flow_signature(flow) == wanted:
            return flow
    return None


def _flow_signature(flow: Flow) -> tuple:
    steps: list[FlowStep] = []
    for node in flow.nodes.filter(node_type="action").order_by("position"):
        cfg = node.config if isinstance(node.config, dict) else {}
        executor = (node.action.executor if node.action else "shell") or "shell"
        steps.append(
            FlowStep(
                executor=executor,
                argv=[str(part) for part in cfg.get("argv") or []],
                extra=dict(cfg.get("extra") or {}),
                security_level=node.action.security_level if node.action else None,
            )
        )
    return steps_signature(steps)


def argv_from_proposal_action(proposal: HermesProposal) -> list[str]:
    if not proposal.actions:
        return []
    return argv_from_action(proposal.actions[0])
