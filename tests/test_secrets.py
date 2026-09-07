from core.secrets import collect_secret_values, redact, resolve_env_refs


def test_redact_known_secret() -> None:
    assert redact("token=abc123secret", ["abc123secret"]) == "token=***"


def test_collect_from_env() -> None:
    values = collect_secret_values({"JELLYFIN_API_KEY": "super-secret-key", "PATH": "/usr/bin"})
    assert "super-secret-key" in values
    assert "/usr/bin" not in values


def test_env_refs(monkeypatch) -> None:
    monkeypatch.setenv("JELLYFIN_URL", "http://media.local")
    assert resolve_env_refs("${JELLYFIN_URL}/Items") == "http://media.local/Items"
