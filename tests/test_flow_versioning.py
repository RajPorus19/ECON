import pytest

from apps.flows.models import Action, Flow, FlowNode
from apps.knowledge.learning import clone_flow_version, persist_proposal, record_alias_candidate
from apps.knowledge.models import Alias, AliasCandidate, Entity, Intent
from core.llm import ActionProposal, EntityProposal, FlowProposal, HermesProposal, IntentProposal
from core.normalize import normalize


@pytest.mark.django_db
def test_clone_flow_does_not_mutate_source() -> None:
    intent = Intent.objects.create(name="launch_program")
    flow = Flow.objects.create(name="launch firefox", intent=intent, version=1, confidence=0.8)
    action = Action.objects.create(name="shell.execute", type="shell", executor="shell")
    FlowNode.objects.create(
        flow=flow,
        node_key="execute",
        node_type="action",
        action=action,
        position=0,
        config={"argv": ["echo", "v1"]},
    )
    clone = clone_flow_version(flow)
    clone.nodes.first().config["argv"] = ["echo", "v2"]
    clone.nodes.first().save()
    flow.refresh_from_db()
    assert flow.version == 1
    assert flow.nodes.first().config["argv"] == ["echo", "v1"]
    assert clone.version == 2
    assert clone.pk != flow.pk


@pytest.mark.django_db
def test_alias_requires_three_confirmations() -> None:
    entity = Entity.objects.create(
        name="Sonic Crossworlds",
        type="game",
        normalized_name="sonic crossworlds",
        confidence=0.8,
    )
    assert (
        record_alias_candidate(
            remainder="sonic", entity=entity, success=True, required_confirmations=3
        )
        is None
    )
    assert (
        record_alias_candidate(
            remainder="sonic", entity=entity, success=True, required_confirmations=3
        )
        is None
    )
    created = record_alias_candidate(
        remainder="sonic", entity=entity, success=True, required_confirmations=3
    )
    assert created is not None
    assert Alias.objects.filter(entity=entity, normalized_alias="sonic").exists()
    assert AliasCandidate.objects.get(entity=entity).confirmations == 3


@pytest.mark.django_db
def test_persist_proposal_creates_versioned_flow() -> None:
    proposal = HermesProposal(
        intent=IntentProposal(name="launch_program", create=False, confidence=0.9),
        entities=[EntityProposal(name="Firefox", type="application", create=True)],
        flow=FlowProposal(create=True, name="launch firefox"),
        actions=[ActionProposal(argv=["echo", "firefox"])],
    )
    flow = persist_proposal(proposal, ["echo", "firefox"])
    assert flow is not None
    assert flow.version == 1
    again = persist_proposal(proposal, ["echo", "firefox"])
    assert again is not None
    assert again.version == 2
    assert again.pk != flow.pk
    assert Entity.objects.filter(normalized_name=normalize("Firefox")).exists()


@pytest.mark.django_db
def test_patch_nodes_creates_new_version(client) -> None:
    intent = Intent.objects.create(name="launch_program")
    flow = Flow.objects.create(name="launch firefox", intent=intent, version=1, confidence=0.8)
    action = Action.objects.create(name="shell.execute", type="shell", executor="shell")
    node = FlowNode.objects.create(
        flow=flow,
        node_key="execute",
        node_type="action",
        action=action,
        position=0,
        config={"argv": ["echo", "v1"]},
    )
    response = client.patch(
        f"/api/v1/flows/{flow.pk}",
        data={
            "name": "launch firefox",
            "nodes": [
                {
                    "id": node.pk,
                    "node_key": "execute",
                    "node_type": "action",
                    "position": 0,
                    "x": 12,
                    "y": 40,
                    "config": {"argv": ["echo", "v1"]},
                }
            ],
            "edges": [],
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] != flow.pk
    assert body["version"] == 2
    flow.refresh_from_db()
    assert flow.enabled is False
