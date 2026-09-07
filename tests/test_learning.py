from core.compiler import compile_proposal
from core.learning import (
    next_confirmation_count,
    should_promote_alias,
    template_text,
    trigger_phrases,
)
from core.llm import ActionProposal, EntityProposal, HermesProposal, IntentProposal


def test_does_not_promote_after_one_use() -> None:
    assert should_promote_alias(1) is False
    assert should_promote_alias(2) is False
    assert should_promote_alias(3) is True


def test_confirmation_counter() -> None:
    assert next_confirmation_count(0, matched_ambiguously=True, success=True) == 1
    assert next_confirmation_count(2, matched_ambiguously=True, success=True) == 3
    assert next_confirmation_count(2, matched_ambiguously=False, success=True) == 2
    assert next_confirmation_count(1, matched_ambiguously=True, success=False) == 0


def test_template_text_replaces_entity() -> None:
    assert template_text("add Dune now", ["Dune"]) == "add {query} now"


def test_trigger_phrases_split_query() -> None:
    phrases = trigger_phrases(normalized="find dune", query="dune", extra=["find me"])
    assert "find dune" in phrases
    assert "find" in phrases


def test_compile_http_action() -> None:
    proposal = HermesProposal(
        intent=IntentProposal(name="add_media"),
        entities=[EntityProposal(name="Dune", type="movie")],
        actions=[
            ActionProposal(
                type="http",
                extra={
                    "url": "http://127.0.0.1:7878/api/v3/movie",
                    "method": "POST",
                    "body": {"title": "Dune"},
                },
            )
        ],
    )
    steps = compile_proposal(proposal)
    assert len(steps) == 1
    assert steps[0].executor == "http"
    assert steps[0].extra["body"]["title"] == "Dune"
