from pathlib import Path

from core.yamlcfg import load_econom_config, load_yaml_file


def test_yaml_defaults(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "econom.yaml"
    path.write_text("econom:\n  matching:\n    confidence_threshold: 0.77\n", encoding="utf-8")
    monkeypatch.delenv("ECON_CONFIDENCE_THRESHOLD", raising=False)
    cfg = load_econom_config(path)
    assert cfg.confidence_threshold == 0.77


def test_env_overrides_yaml(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "econom.yaml"
    path.write_text("econom:\n  matching:\n    confidence_threshold: 0.77\n", encoding="utf-8")
    monkeypatch.setenv("ECON_CONFIDENCE_THRESHOLD", "0.91")
    cfg = load_econom_config(path)
    assert cfg.confidence_threshold == 0.91


def test_missing_file() -> None:
    assert load_yaml_file(Path("/tmp/does-not-exist-econ.yaml")) == {}
