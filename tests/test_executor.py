from core.compiler import argv_from_action
from core.execution import ExecuteRequest
from core.execution.local import LocalSubprocessExecutor
from core.llm import ActionProposal


def test_local_echo() -> None:
    result = LocalSubprocessExecutor().execute(ExecuteRequest(argv=["echo", "hello-econ"]))
    assert result.success
    assert "hello-econ" in result.stdout


def test_argv_from_command_string() -> None:
    assert argv_from_action(ActionProposal(command="echo hello")) == ["echo", "hello"]
