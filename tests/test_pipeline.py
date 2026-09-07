from core.cache import CachedResolution, MemoryPhraseCache
from core.engine import Pipeline
from core.execution import ExecuteRequest, ExecuteResult
from core.llm import ActionProposal, HermesProposal, IntentProposal, LLMResult, LLMUsage


class EmptyKnowledge:
    def intent_aliases(self) -> list[tuple[str, str, float]]:
        return [("lance", "launch_program", 1.0)]

    def entity_names(self) -> list[tuple[str, str, float]]:
        return [("firefox", "Firefox", 1.0)]

    def find_flow(self, intent_name: str, entity_name: str | None):
        if intent_name == "launch_program" and entity_name == "Firefox":
            return ("1", 0.99, ["echo", "firefox"])
        return None


class RecordingExecutor:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def execute(self, request: ExecuteRequest) -> ExecuteResult:
        self.calls.append(request.argv)
        return ExecuteResult(success=True, exit_code=0, stdout="ok")


class FakeLLM:
    def generate_structured(self, payload: dict) -> LLMResult:
        return LLMResult(
            proposal=HermesProposal(
                intent=IntentProposal(name="shell_execute", create=False),
                actions=[ActionProposal(argv=["echo", "compiled"])],
            ),
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5),
            model="fake",
        )

    def ping(self) -> bool:
        return True


def test_known_flow_skips_llm() -> None:
    executor = RecordingExecutor()
    pipeline = Pipeline(knowledge=EmptyKnowledge(), executor=executor, llm=FakeLLM())
    result = pipeline.run("Lance Firefox")
    assert result.status == "success"
    assert result.llm_used is False
    assert executor.calls == [["echo", "firefox"]]
    assert result.tokens_saved == 1200


def test_unknown_request_uses_llm() -> None:
    executor = RecordingExecutor()
    pipeline = Pipeline(knowledge=EmptyKnowledge(), executor=executor, llm=FakeLLM())
    result = pipeline.run("do something new")
    assert result.status == "success"
    assert result.llm_used is True
    assert executor.calls == [["echo", "compiled"]]


def test_l1_cache_skips_matcher_and_llm() -> None:
    cache = MemoryPhraseCache()
    cache.put_exact(
        "Lance Firefox",
        CachedResolution(flow_id="9", argv=["echo", "cached"], flow_confidence=1.0),
    )
    executor = RecordingExecutor()
    pipeline = Pipeline(knowledge=EmptyKnowledge(), executor=executor, llm=FakeLLM(), cache=cache)
    result = pipeline.run("Lance Firefox")
    assert result.llm_used is False
    assert result.cache_layer == "L1"
    assert executor.calls == [["echo", "cached"]]


class LowConfidenceKnowledge(EmptyKnowledge):
    def find_flow(self, intent_name: str, entity_name: str | None):
        if intent_name == "launch_program" and entity_name == "Firefox":
            return ("1", 0.40, ["echo", "firefox"])
        return None


def test_below_threshold_falls_back_to_llm() -> None:
    executor = RecordingExecutor()
    pipeline = Pipeline(
        knowledge=LowConfidenceKnowledge(),
        executor=executor,
        llm=FakeLLM(),
        confidence_threshold=0.90,
    )
    result = pipeline.run("Lance Firefox")
    assert result.llm_used is True
    assert executor.calls == [["echo", "compiled"]]
