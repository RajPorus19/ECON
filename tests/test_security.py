from core.security import Decision, evaluate


def test_echo_is_auto() -> None:
    verdict = evaluate(["echo", "hello"])
    assert verdict.decision is Decision.AUTO


def test_rm_rf_root_is_denied() -> None:
    verdict = evaluate(["rm", "-rf", "/"])
    assert verdict.decision is Decision.DENY


def test_rm_file_requires_confirm() -> None:
    verdict = evaluate(["rm", "notes.txt"])
    assert verdict.decision is Decision.CONFIRM
    confirmed = evaluate(["rm", "notes.txt"], confirmed=True)
    assert confirmed.decision is Decision.AUTO


def test_shutdown_requires_confirm() -> None:
    verdict = evaluate(["shutdown", "-h", "now"])
    assert verdict.decision is Decision.CONFIRM


def test_policy_can_deny_filesystem() -> None:
    from core.security import SecurityPolicy

    verdict = evaluate(["rm", "notes.txt"], policy=SecurityPolicy(filesystem=Decision.DENY))
    assert verdict.decision is Decision.DENY


def test_empty_argv_denied() -> None:
    assert evaluate([]).decision is Decision.DENY
