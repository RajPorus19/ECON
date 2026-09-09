from core.compiler import compile_action, compile_proposal
from core.execution import FlowStep
from core.llm import (
    ActionProposal,
    EntityProposal,
    HermesProposal,
    IntentProposal,
    ProviderProposal,
)


def test_provider_action_resolves_to_http_step() -> None:
    action = ActionProposal(type="provider", command="jellyfin.search", argv=[])
    step = compile_action(action)
    assert step.executor == "http"
    assert "/Items?searchTerm={query}" in step.extra["url"]


def test_provider_play_resolves_to_http_step() -> None:
    action = ActionProposal(type="provider", command="jellyfin.play", argv=[])
    step = compile_action(action)
    assert step.executor == "http"
    assert "/Sessions/" in step.extra["url"]


def test_steam_launch_resolves_to_shell_step() -> None:
    action = ActionProposal(type="provider", command="steam.launch", argv=[])
    step = compile_action(action)
    assert step.executor == "shell"
    assert step.argv[:2] == ["steam", "steam://rungameid/{app_id}"]


def test_plain_shell_command_still_shell() -> None:
    action = ActionProposal(type="shell", argv=["echo", "hi"])
    step = compile_action(action)
    assert step.executor == "shell"
    assert step.argv == ["echo", "hi"]


def test_play_media_composes_search_then_play() -> None:
    proposal = HermesProposal(
        intent=IntentProposal(name="play_media", create=False, confidence=0.95),
        provider=ProviderProposal(name="Jellyfin", create=False),
        entities=[EntityProposal(name="Souleymane", type="media", create=True)],
        actions=[
            ActionProposal(type="provider", command="jellyfin.play", argv=[]),
        ],
    )
    steps = compile_proposal(proposal)
    assert len(steps) == 2
    assert steps[0].executor == "http" and "searchTerm={query}" in steps[0].extra["url"]
    assert steps[1].executor == "http" and "/Sessions/" in steps[1].extra["url"]


def test_proposal_with_provider_actions_compiles() -> None:
    proposal = HermesProposal(
        provider=ProviderProposal(name="Jellyfin", create=False),
        entities=[
            EntityProposal(name="L'Histoire de Souleymane", type="movie", create=True)
        ],
        actions=[
            ActionProposal(type="provider", command="jellyfin.search", argv=[]),
            ActionProposal(type="provider", command="jellyfin.play", argv=[]),
        ],
    )
    steps = compile_proposal(proposal)
    assert len(steps) == 2
    assert all(isinstance(s, FlowStep) for s in steps)
    assert steps[0].executor == "http"
    assert steps[1].executor == "http"
