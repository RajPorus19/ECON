"""Persist Hermes proposals into versioned knowledge. Never mutate an existing flow body."""

from __future__ import annotations

from django.utils import timezone

from apps.flows.models import Action, ActionVersion, Flow, FlowEdge, FlowNode
from apps.knowledge.models import Alias, AliasCandidate, Entity, Intent, IntentAlias, Provider
from core.compiler import argv_from_action
from core.confidence import apply_outcome
from core.learning import next_confirmation_count, should_promote_alias
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


def persist_proposal(proposal: HermesProposal, argv: list[str]) -> Flow | None:
    intent = None
    if proposal.intent:
        intent, _ = Intent.objects.get_or_create(
            name=proposal.intent.name,
            defaults={"confidence": proposal.intent.confidence or 0.7},
        )
        if proposal.intent.create:
            IntentAlias.objects.get_or_create(
                normalized_phrase=normalize(proposal.intent.name.replace("_", " ")),
                defaults={
                    "intent": intent,
                    "phrase": proposal.intent.name.replace("_", " "),
                    "confidence": proposal.intent.confidence or 0.7,
                },
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

    action = Action.objects.filter(name="shell.execute").first()
    if action is None:
        action = Action.objects.create(
            name="shell.execute",
            type="shell",
            executor="shell",
            security_level=1,
        )
        ActionVersion.objects.create(
            action=action,
            version=1,
            definition={"executor": "shell", "argv": argv},
            enabled=True,
            verified=False,
        )

    flow_name = proposal.flow.name if proposal.flow and proposal.flow.name else None
    if not flow_name:
        bits = [intent.name if intent else "request"]
        if entity:
            bits.append(entity.name)
        flow_name = " / ".join(bits)

    flow = Flow.objects.create(
        name=flow_name,
        intent=intent,
        version=next_flow_version(flow_name),
        confidence=0.7,
        enabled=True,
    )
    resolve = FlowNode.objects.create(
        flow=flow,
        node_key="resolve_entity",
        node_type="resolve_entity",
        entity=entity,
        provider=provider,
        position=0,
    )
    execute = FlowNode.objects.create(
        flow=flow,
        node_key="execute",
        node_type="action",
        action=action,
        entity=entity,
        provider=provider,
        position=1,
        config={"argv": argv},
    )
    FlowEdge.objects.create(flow=flow, source_node=resolve, target_node=execute)
    return flow


def argv_from_proposal_action(proposal: HermesProposal) -> list[str]:
    if not proposal.actions:
        return []
    return argv_from_action(proposal.actions[0])
