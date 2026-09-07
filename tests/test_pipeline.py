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
            usage=LLMUsage(),
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


def test_unknown_request_uses_llm() -> None:
    executor = RecordingExecutor()
    pipeline = Pipeline(knowledge=EmptyKnowledge(), executor=executor, llm=FakeLLM())
    result = pipeline.run("do something new")
    assert result.status == "success"
    assert result.llm_used is True
    assert executor.calls == [["echo", "compiled"]]
